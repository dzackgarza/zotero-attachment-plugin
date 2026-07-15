"""Stateful live proof of the multi-item merge/restore/trash workflow.

Every mutation is the same ``POST /write`` operation and the workflow must
keep several independent handles alive at once (source item, target item,
collection, note, tags), which OpenAPI Links cannot express. So this is a
hand-written Hypothesis ``RuleBasedStateMachine`` that drives real ``Case``
objects built from the canonical operation, validates each request body
against the resolved OpenAPI component (``contract.validate_write_body``),
lets ``call_and_validate`` check status/content-type/response-schema, and then
independently verifies Zotero's final state through the built-in read-only
local API. A write response reporting success is not accepted as proof; the
read-back is.

The suite mutates a real Zotero library, so every object is uniquely prefixed
and cleaned up in ``teardown`` even on failure. Dangerous/networked/bulk
operations are never exercised here. Scenarios are serialized because they
share one Zotero process.
"""

from __future__ import annotations

import pytest
import schemathesis
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    precondition,
    rule,
)

from tests.schemathesis import contract, helpers


pytestmark = pytest.mark.skipif(
    not helpers.zotero_reachable(),
    reason="No live Zotero add-on reachable at the configured base URL.",
)

_SCHEMA = schemathesis.openapi.from_path(
    str(contract._SPEC_PATH)  # single source of truth
)
_WRITE = _SCHEMA["/write"]["POST"]


class ZoteroWriteWorkflow(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.uid = ""
        self.step = 0
        self.collection_key: str | None = None
        self.source_key: str | None = None
        self.target_key: str | None = None
        self.note_key: str | None = None
        self.keep_tag = ""
        self.remove_tag = ""

    # ── setup ────────────────────────────────────────────────────

    @initialize(token=st.uuids(version=4))
    def seed(self, token) -> None:
        # The unique prefix is drawn by Hypothesis (not uuid4 in __init__) so
        # scenarios are deterministic and replayable during shrinking.
        self.uid = token.hex[:12]
        self.keep_tag = f"lw-keep-{self.uid}"
        self.remove_tag = f"lw-remove-{self.uid}"

    # ── request/response plumbing ────────────────────────────────

    def _send(self, body: dict) -> dict:
        """Validate the body against the contract, send it, and let
        Schemathesis validate the response, then return the parsed JSON."""
        contract.validate_write_body(body)
        case = _WRITE.Case(body=body, media_type="application/json")
        # A generous timeout: the single Zotero process can be slow under a
        # back-to-back workflow, and a read timeout would surface to Hypothesis
        # as spurious flakiness rather than a contract failure.
        response = case.call_and_validate(
            base_url=helpers.base_url(), timeout=60
        )
        payload = response.json()
        assert payload.get("success") is True, f"write not successful: {payload!r}"
        return payload

    # ── ordered workflow ─────────────────────────────────────────

    @precondition(lambda self: self.step == 0)
    @rule()
    def setup_collection(self) -> None:
        payload = self._send(
            {"operation": "create_collection", "name": f"lw-col-{self.uid}"}
        )
        self.collection_key = payload["details"]["collection_key"]
        assert self.collection_key
        self.step = 1

    @precondition(lambda self: self.step == 1)
    @rule()
    def create_source(self) -> None:
        title = f"lw-source-{self.uid}"
        payload = self._send(
            {"operation": "create_item", "item_type": "book", "fields": {"title": title}}
        )
        self.source_key = payload["item_key"]
        assert self.source_key
        assert helpers.get_item(self.source_key)["data"]["title"] == title
        self.step = 2

    @precondition(lambda self: self.step == 2)
    @rule()
    def attach_note(self) -> None:
        payload = self._send(
            {
                "operation": "attach_note",
                "parent_item_key": self.source_key,
                "note_text": f"note-{self.uid}",
            }
        )
        self.note_key = payload["note_key"]
        assert self.note_key
        children = helpers.get_children(self.source_key)
        assert any(child.get("key") == self.note_key for child in children), (
            f"note {self.note_key} not a child of source: {children!r}"
        )
        self.step = 3

    @precondition(lambda self: self.step == 3)
    @rule()
    def assign_collection(self) -> None:
        self._send(
            {
                "operation": "add_item_to_collection",
                "item_key": self.source_key,
                "collection_key": self.collection_key,
            }
        )
        collections = helpers.get_item(self.source_key)["data"].get("collections", [])
        assert self.collection_key in collections, f"source not in collection: {collections!r}"
        self.step = 4

    @precondition(lambda self: self.step == 4)
    @rule()
    def add_tags(self) -> None:
        self._send(
            {
                "operation": "add_item_tags",
                "item_key": self.source_key,
                "tags": [self.keep_tag, self.remove_tag],
            }
        )
        tags = helpers.tag_names(helpers.get_item(self.source_key))
        assert {self.keep_tag, self.remove_tag} <= tags, f"tags missing: {tags!r}"
        self.step = 5

    @precondition(lambda self: self.step == 5)
    @rule()
    def remove_tags(self) -> None:
        self._send(
            {
                "operation": "remove_item_tags",
                "item_key": self.source_key,
                "tags": [self.remove_tag],
            }
        )
        tags = helpers.tag_names(helpers.get_item(self.source_key))
        assert self.remove_tag not in tags, f"remove tag survived: {tags!r}"
        assert self.keep_tag in tags, f"keep tag lost: {tags!r}"
        self.step = 6

    @precondition(lambda self: self.step == 6)
    @rule()
    def create_target(self) -> None:
        payload = self._send(
            {
                "operation": "create_item",
                "item_type": "book",
                "fields": {"title": f"lw-target-{self.uid}"},
            }
        )
        self.target_key = payload["item_key"]
        assert self.target_key
        self.step = 7

    @precondition(lambda self: self.step == 7)
    @rule()
    def merge(self) -> None:
        payload = self._send(
            {
                "operation": "merge_items",
                "source_key": self.source_key,
                "target_key": self.target_key,
            }
        )
        transferred = payload["details"]["transferred"]
        for field in ("attachments", "notes", "tags", "relations"):
            assert isinstance(
                transferred[field], int
            ), f"transfer counter {field} not int: {transferred!r}"
        assert transferred["notes"] >= 1, f"expected note transfer: {transferred!r}"

        # Zotero's trash is deferred, so the source's deleted flag is the one
        # value that must be polled (same as live_smoke's _wait_for_deleted).
        assert helpers.wait_for(
            lambda: helpers.is_deleted(self.source_key)
        ), "merged source not deleted"
        target = helpers.get_item(self.target_key)
        assert not target["data"].get("deleted"), "merge target deleted"
        target_children = helpers.get_children(self.target_key)
        assert any(child.get("key") == self.note_key for child in target_children), (
            f"note did not move under target: {target_children!r}"
        )
        assert self.keep_tag in helpers.tag_names(target), "kept tag did not transfer to target"
        self.step = 8

    @precondition(lambda self: self.step == 8)
    @rule()
    def restore(self) -> None:
        self._send({"operation": "restore_item", "item_key": self.source_key})
        assert helpers.wait_for(
            lambda: not helpers.is_deleted(self.source_key)
        ), "restore_item did not clear deleted flag"
        self.step = 9

    @precondition(lambda self: self.step == 9)
    @rule()
    def trash(self) -> None:
        self._send({"operation": "trash_item", "item_key": self.source_key})
        assert helpers.wait_for(
            lambda: helpers.is_deleted(self.source_key)
        ), "trash_item did not set deleted flag"
        self.step = 10

    @precondition(lambda self: self.step == 10)
    @rule()
    def final_state(self) -> None:
        # Re-read every retained handle and confirm the end state. Collection
        # membership is not asserted post-merge: merge_items does not transfer
        # it in current code, so this only re-reads what must still hold.
        assert helpers.is_deleted(self.source_key), "final: source not trashed"
        target = helpers.get_item(self.target_key)
        assert not target["data"].get("deleted"), "final: target deleted"
        assert self.keep_tag in helpers.tag_names(target), "final: kept tag missing"
        self.step = 11

    def teardown(self) -> None:
        # Trash the objects this scenario actually created. Keys are None only
        # when the scenario failed before creating that object. Trash is
        # idempotent, so re-trashing the already-trashed source is fine; if a
        # trash fails here Zotero is genuinely broken and that must surface.
        for item_key in (self.source_key, self.target_key):
            if item_key:
                helpers.trash_item(item_key)
        if self.collection_key:
            helpers.trash_collection(self.collection_key)


# At least 12 steps: the 11-rule linear workflow cannot complete under
# Hypothesis's default of 6 steps per scenario.
ZoteroWriteWorkflow.TestCase.settings = settings(
    max_examples=1,
    stateful_step_count=12,
    deadline=None,
)

TestZoteroWriteWorkflow = ZoteroWriteWorkflow.TestCase

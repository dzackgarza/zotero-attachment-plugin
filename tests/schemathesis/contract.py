"""Resolve and validate /write request bodies against the canonical schema.

The stateful workflow must retain several independent handles (source item,
target item, collection, note, tags), which OpenAPI Links cannot express, so
bodies are built in code. To guarantee those hand-built bodies never drift
into a second, unvalidated schema, each one is validated against the request
component resolved from ``WriteRequest.discriminator.mapping`` before it is
sent. There is exactly one schema: ``openapi.yaml``.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012


_SPEC_PATH = Path(__file__).resolve().parents[2] / "openapi.yaml"
_BASE_URI = "urn:openapi"


@functools.lru_cache(maxsize=1)
def _spec() -> dict[str, Any]:
    return yaml.safe_load(_SPEC_PATH.read_text())


@functools.lru_cache(maxsize=1)
def _registry() -> Registry:
    resource = Resource(contents=_spec(), specification=DRAFT202012)
    return Registry().with_resource(uri=_BASE_URI, resource=resource)


@functools.lru_cache(maxsize=1)
def _mapping() -> dict[str, str]:
    return _spec()["components"]["schemas"]["WriteRequest"]["discriminator"]["mapping"]


def request_component_ref(operation: str) -> str:
    """The ``#/components/...`` ref for an operation's request schema."""
    mapping = _mapping()
    if operation not in mapping:
        raise KeyError(
            f"operation {operation!r} is not in WriteRequest.discriminator.mapping"
        )
    return mapping[operation]


def validate_write_body(body: dict[str, Any]) -> dict[str, Any]:
    """Validate a /write body against its resolved request component.

    Returns the body unchanged so callers can inline the check. Raises
    ``jsonschema.ValidationError`` if the hand-built body does not conform to
    the canonical contract.
    """
    operation = body.get("operation")
    if not isinstance(operation, str):
        raise ValueError(f"body has no string operation: {body!r}")
    ref = request_component_ref(operation)
    Draft202012Validator(
        {"$ref": _BASE_URI + ref}, registry=_registry()
    ).validate(body)
    return body

"""Schemathesis hooks for the generic fuzzing run.

All 32 write variants share one HTTP operation (``POST /write``), so path or
operationId filters cannot exclude an individual body variant. This
``filter_case`` hook inspects the generated body's ``operation`` and drops
positive cases for operations that execute arbitrary code, contact the
network, or perform irreversible/bulk mutations that must not run during
generic fuzzing.

``filter_case`` feeds a Hypothesis ``.filter()``: returning ``True`` keeps the
case, ``False`` skips it. Negative cases (missing/unknown ``operation``, or a
malformed body that is not a dict) do not carry a dangerous ``operation``
value and are therefore preserved, so rejection behavior is still exercised.

Coverage-phase cases bypass component-level body hooks, so the exclusion is
enforced here at the case level as the plan requires.
"""

from __future__ import annotations

import schemathesis


# Operations excluded from generated positive cases:
# - run_javascript: executes arbitrary code inside Zotero;
# - sync: contacts the network and mutates remote state;
# - import_by_identifier: contacts the network;
# - import_bibtex: bulk-creates items from free-form input;
# - delete_unused_tags: irreversible bulk mutation across the library.
DANGEROUS_OPERATIONS = frozenset(
    {
        "run_javascript",
        "sync",
        "import_by_identifier",
        "import_bibtex",
        "delete_unused_tags",
    }
)


@schemathesis.hook
def filter_case(context, case) -> bool:
    body = case.body
    if isinstance(body, dict) and body.get("operation") in DANGEROUS_OPERATIONS:
        return False
    return True

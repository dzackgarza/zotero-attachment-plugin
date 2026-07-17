## Summary

<!-- What this PR does, and the issue(s) it closes / references.
-->

## Issue-scoped lifecycle gate — required

- [ ] Linked triaged issue(s): #____
- [ ] This PR started as a draft while implementation/proof was in progress.
- [ ] The PR scope maps to the linked issue acceptance criteria; unrelated issue families are excluded.
- [ ] Ready-for-review was requested only after the policy alignment gate and evidence below were complete.
- [ ] Returned review feedback followed [pr-feedback-triage](https://github.com/dzackgarza/ai-review-ci/blob/main/skills/pr-feedback-triage/SKILL.md): every resolved substantive item carries its own evidenced disposition, and accepted or modified feedback cites committed remediation and proof.

## Policy alignment gate — required

<!-- policy-alignment-gate -->

Authoritative policy lives in-repo: `skills/policy-index/SKILL.md` + `skills/policy-index/references/policies.md`. Load it **from this checkout** — do not rely on globally-installed skills (remote agents do not have them).
Full rationale: AGENTS.md → **Policy Alignment Gate** and the wiki [Policy Alignment Gate](https://github.com/dzackgarza/ai-review-ci/wiki/Policy-Alignment-Gate).

### Tier 0 — every PR

- [ ] Loaded the canonical `POLICY.*` records.
  Codes this change touches or risks: `POLICY.____`
- [ ] No **Invalid local fix** introduced — no new fallback, runtime default, optional core-state, swallowed error, or partial-success path that makes required work look successful after it should fail loudly.
- [ ] No empty/falsy-literal fallback (`""`, `[]`, `{}`, `null`, `false`, `0`) added or reclassified as "safe."
  Optional state is an explicit typed state at the boundary.

### Tier 1 — QC-tooling changes

Check the one line that applies (both are valid answers, so this never blocks a non-QC PR):

- [ ] **Not applicable** — this PR touches none of `tool-configs/`, `reviews/`, detectors, or QC `justfiles/`; **or** it does, and: a `ruleid`/equivalent **regression-lock** fixture proves each previously-flagged banned pattern still fires (precision narrows by *position*, never *value*), the change weakens no `POLICY.*` / silences no true finding, and any policy-*semantics* change edits the canonical records in `skills/policy-index/` directly (this repo owns them).

## Evidence

<!-- Commands, fixtures, and test output proving the boxes above.
Not assertions — artifacts.
-->

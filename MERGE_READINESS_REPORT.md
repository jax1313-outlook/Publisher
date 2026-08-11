# MERGE READINESS REPORT — Publisher

Program: Dispatch
Department: Publisher
Build: Tri-Department Matrix Build (Intelligence → Library → Publisher)
Date: 2026-08-11

---

## 1. Status

**Integration-ready candidate.** Not merged into Dispatch. Not deployed. Not production-promoted.
Per 07_DISPATCH_REPO_PLACEMENT_PLAN.md Section 3, this repo is at "Integration-ready candidate"
and awaits Claude Code cross-repo review, Hold/Test-Grounds, then Mike approval.

## 2. Required Outputs (Build Command Section 4.3 / 6 / 9)

| Required | Present |
|---|---|
| Recipe registry (consumption side) | Yes — `library_client.py` + `models.RecipeType`; recipe storage itself lives in Library per the shared contract |
| Publisher request model | Yes — `models.PublisherRequest` |
| Readiness packet | Yes — `service.create_readiness_packet` |
| Workspace model | Yes — `models.Workspace`, populated by `service.pull_libraries` |
| Library pull logic | Yes — `service.pull_libraries` via `LibraryClient` |
| Parts inventory | Yes — `service.create_inventory` |
| Missing-item notice | Yes — `service.create_missing_notice` |
| Draft review package | Yes — `service.create_review_package` / `approve_review_package` |
| Broker onboarding packet candidate | Recipe type present (`RecipeType.BROKER_ONBOARDING_PACKET`); full packet content generation is downstream of readiness/review objects — see Known Gaps |
| Government proposal package candidate | Recipe type present (`RecipeType.GOVERNMENT_PROPOSAL_PACKET`); same note |
| Visibility/evidence bundle candidate | Yes — `service.create_visibility_package`, `service.create_pod_bundle` |
| Archive handoff package | Yes — `service.create_archive_handoff` (blocked without approval) |
| Tests | Yes — 19 tests, 19 passing |
| README | Yes |
| Merge readiness report | This document |

## 3. Test Summary

```
PYTHONPATH=src pytest -q
19 passed
```

Covers: recipe/library pull no-fabrication (missing object codes reported, not invented),
readiness packet lists every required item (Library and Intelligence-sourced), readiness overall
status logic, parts inventory gap visibility, missing-item notice creation and its `None`-when-
nothing-missing behavior, `MissingItemNotice.recipient_hint` rejecting external identities,
review-package self-approval rejection, review-package approval requiring an external identity,
double-finalization rejection, Archive handoff blocked without approval and succeeding after,
visibility package `NOT_SENT` invariant (including that it cannot be overridden via constructor),
POD bundle completeness reflecting missing evidence, and a structural AST scan proving no
network-capable import or send/submit-named function exists anywhere in the package.

## 4. Matrix Compliance Test (System Relationship Matrix Section 12)

| Question | Answer |
|---|---|
| What object is created? | `PublisherRequest`, `Workspace`, `ReadinessPacket`, `PartsInventory`, `MissingItemNotice`, `DraftReviewPackage`, `ArchiveHandoffPackage`, `VisibilityPackage`, `PODEvidenceBundle` |
| Who owns it? | Publisher |
| Where is it stored? | In-process objects returned to the caller; no repo-owned persistence layer (see Known Gaps) |
| Temporary, current truth, or history? | All temporary/draft until human-approved; `ArchiveHandoffPackage` is the handoff into history, owned by Archive once received |
| Who consumes it? | Human, Manager, Portal, Archive (handoff only) |
| Who may not consume it? | Customer, Broker, Government — no code path reaches them in this repo |
| Review requirement? | Yes — every review package requires human review before archival |
| Approval requirement? | Yes — `APPROVED_BY_MIKE` only via external `approver_id` |
| Library candidate? | Publisher may nominate Library candidates via the Library repo's `LibraryCandidate`/`submit_candidate` (Intelligence repo ships the reference implementation of that pattern; Publisher's equivalent nomination call is a documented integration point, not yet wired — see Known Gaps) |
| Archive requirement? | Yes — `ArchiveHandoffPackage`, gated on approval |
| Portal card? | Not created directly by this repo — Manager/Portal integration out of scope |
| Work item? | Not created directly by this repo |
| Test coverage? | Yes, see Section 3 |
| Forbidden path created? | None identified — see Section 5 |
| Reduces Mike's cognitive load? | Yes — one review package summarizes present/missing state instead of manual cross-checking |

## 5. Hard Rule / Forbidden Path Verification

- Publisher may not approve itself: verified by `test_review_package_cannot_approve_itself`.
- Publisher may not submit externally: verified structurally by `tests/test_no_external_send.py` (AST scan, not just convention).
- No invented facts / no-fabrication: verified by `test_pull_libraries_reports_missing_not_fabricated` and `test_requirement_types_present_does_not_fabricate`.
- No promotion of drafts into Library truth: no code path in this repo writes to a Library registry; Publisher only reads via `LibraryClient`.
- No Mike bypass: `approve_review_package`/`reject_review_package` both require an external, non-system identity, tested.
- Archive handoff blocked without approval: verified by `test_archive_handoff_blocked_without_approval`.

## 6. Known Gaps

See `KNOWN_GAPS.md`.

## 7. Recommendation

This is a recommendation only. No merge, deployment, or promotion is authorized by this report.
Mike decides.

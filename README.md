# Dispatch Publisher

Publisher department implementation for the Dispatch program (Level 1 Transport / Mike Zachary).
This repo builds the **Publisher** link of the Intelligence → Library → Publisher dependency
chain defined in `04_DISPATCH_SYSTEM_RELATIONSHIP_MATRIX.md` — the last link, consuming both
upstream departments.

> Legacy note: this repo's prior README described it as "Test-Grounds". Per
> `07_DISPATCH_REPO_PLACEMENT_PLAN.md` ("Publisher Repo"), this repository's actual role is to
> build and test the Publisher department to integration-ready status. The Hold/Test-Grounds
> repo referenced by the Repo Placement Plan's promotion flow is a separate GitHub repo
> (`jax1313-outlook/Test-Grounds`), not this one.

## Status

**Integration-ready candidate.** Not merged into Dispatch. Not deployed. Not production-promoted.
See `MERGE_READINESS_REPORT.md` and `KNOWN_GAPS.md`. Mike decides on promotion.

## What this repo does

Publisher is a governed production assembly department: it drafts, it never approves itself, and
it never sends anything externally. `src/dispatch_publisher/`:

- **`models.py`** — `PublisherRequest`, `Workspace`, `ReadinessPacket`, `PartsInventory`,
  `MissingItemNotice`, `DraftReviewPackage`, `ArchiveHandoffPackage`, `VisibilityPackage`,
  `PODEvidenceBundle`, matching `DISPATCH_SHARED_OBJECT_CONTRACTS_v1.md` Section 5.
- **`library_client.py`** / **`intelligence_client.py`** — duck-typed integration boundaries
  Publisher uses to call into the Library and Intelligence repos' service surfaces, without a
  hard package dependency on either (the three repos are independently built, per the Repo
  Placement Plan). Each ships an in-process stub for local/offline testing.
- **`service.py`** — the full assembly pipeline: `create_request` → `pull_libraries` →
  `create_readiness_packet` → `create_inventory` → `create_missing_notice` →
  `create_review_package` → `approve_review_package` → `create_archive_handoff`, plus
  `create_visibility_package` and `create_pod_bundle`.

## The approval gate (Hard Rule: Publisher may not approve itself)

`create_review_package` can only produce `DRAFT` or `REVIEW_READY` — never `APPROVED_BY_MIKE`.
The only function that can set `APPROVED_BY_MIKE` is `approve_review_package(review,
approver_id)`, and it rejects any `approver_id` that is empty or matches a reserved system
identity (`PUBLISHER`, `INTELLIGENCE`, `LIBRARY`, `SYSTEM`, `AUTOMATION`). `create_archive_handoff`
refuses to run unless the referenced review is already `APPROVED_BY_MIKE` — Publisher cannot hand
its own unapproved drafts to Archive as if they were final.

## The no-send guarantee (Hard Rule: Publisher may not submit externally)

There is no networking, email, or external-API code anywhere in this repo.
`tests/test_no_external_send.py` verifies this structurally (AST-scans every module for forbidden
imports and forbidden function-name patterns) rather than relying on convention.
`VisibilityPackage.send_status` and `MissingItemNotice.status` are fixed values with no "SENT"
state reachable from any code path.

## Install / Test

```bash
export PYTHONPATH=$(pwd)/src
pip install pytest
pytest -v
```

See `docs/OBJECT_MODEL.md` for the full schema reference.

## Boundaries (PUBLISHER.md; Repo Placement Plan)

This repo contains no Intelligence interpretation logic, no Library truth ownership, no external
send/submission logic, no autonomous approval, and no deployment logic.

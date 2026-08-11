# OBJECT MODEL

Canonical source: `DISPATCH_SHARED_OBJECT_CONTRACTS_v1.md` in the Claude-3 repo, Section 5. This
page documents this repo's implementation (`src/dispatch_publisher/models.py`).

## Pipeline order

```text
create_request(recipe_code, recipe_type, publisher_requirement_ids)
        │
        ▼
pull_libraries(request, library_client) ──────────> Workspace
        │  (LibraryClient.resolve_packet(); MISSING never fabricated)
        ▼
create_readiness_packet(request, workspace, ...) ──> ReadinessPacket
        │
        ▼
create_inventory(readiness_packet) ────────────────> PartsInventory
        │
        ├──> create_missing_notice(inventory) ──────> MissingItemNotice | None
        │
        ▼
create_review_package(request, packet, inventory, notice) ──> DraftReviewPackage (DRAFT/REVIEW_READY only)
        │
        ▼
approve_review_package(review, approver_id) ───────> DraftReviewPackage (APPROVED_BY_MIKE)
        │        (approver_id must be external — see README)
        ▼
create_archive_handoff(review) ────────────────────> ArchiveHandoffPackage
        (blocked unless review.status == APPROVED_BY_MIKE)
```

`create_visibility_package` and `create_pod_bundle` are independent side-branches (Build Command
§6 rows "Visibility Package M1" / POD Package) — both draft-only, both `NOT_SENT`/Archive-bound,
never customer/broker-reachable in this repo.

## Field notes

- `DraftReviewPackage.status` — `DRAFT | REVIEW_READY | NEEDS_MIKE_DECISION | APPROVED_BY_MIKE |
  REJECTED`. Only `service.approve_review_package` / `service.reject_review_package` can reach the
  two terminal states, and both require an external, non-system `approver_id`/`reviewer_id`.
- `MissingItemNotice.recipient_hint` — constructor (`models.py`) rejects `CUSTOMER`, `BROKER`,
  `GOVERNMENT`, `AGENCY` as values. This is a hard-coded guard, not a suggestion.
- `VisibilityPackage.send_status` and the model's lack of any "SENT" status anywhere is the entire
  no-external-send guarantee for the M1 visibility product line — see `tests/test_no_external_send.py`.

## Integration boundaries

`library_client.LibraryClient` and `intelligence_client.SupportsPublisherRequirement` are
duck-typed `Protocol`s, not imports of the other repos' concrete classes. A real integration
supplies an adapter whose methods match these signatures — for example, wrapping
`dispatch_library.service.LibraryService.current`/`.resolve_packet` directly, since the Library
repo's method signatures were designed to match this Protocol exactly.

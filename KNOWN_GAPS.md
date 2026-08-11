# KNOWN GAPS — Publisher

## Missing source material (Build Command Section 3)

Not found in any repo in scope: `publisher_mvp.py` (Publisher MVP prototype), `publisher_recipes.json`,
Publisher templates, Publisher Constitution Package, Legacy Publisher Emails 1-5,
`quality_control_statement.md`, `submission_email_template.md`, `technical_narrative_template.md`,
`Visibility_SOP.docx`. See `DISPATCH_SHARED_OBJECT_CONTRACTS_v1.md` Section 1 (Claude-3 repo) for
the full cross-department missing-source report. Nothing in this repo invents the content those
documents would define — recipe *types* are doctrine-named (Constitution/PUBLISHER.md), but no
specific packet field content, agency form layout, email copy, or SOP procedure is fabricated.

## Architectural gaps carried forward

- **No content-generation layer.** This repo builds the governed *assembly and gate* machinery
  (request → workspace → readiness → inventory → review → approval → handoff) but does not draft
  actual document/packet text (cover letters, technical narratives, form field values). Build
  Command Section 4.3 lists "broker onboarding packet candidate" and "government proposal package
  candidate" as outputs; this build provides the recipe types and the readiness/review pipeline
  those packets flow through, not prose generation, which requires the missing templates/prototype
  source above plus a Mike-approved drafting-content policy (PUBLISHER.md Section 6/7 governs
  *how* content must be sourced and labeled, but the actual template language is not available in
  any repo in scope).
- **No persistent store.** All `service.py` functions are pure/stateless, returning objects the
  caller must hold. A Dispatch Spine-backed persistence layer is required for a running
  integration.
- **No live Library/Intelligence wiring.** `LibraryClient`/intelligence-requirement consumption are
  Protocol-shaped stubs (`library_client.StubLibraryClient`) for local testing. Wiring to the
  actual `dispatch_library.service.LibraryService` and `dispatch_intel.service` requires a runtime
  that has both repos available (e.g. the Dispatch Spine), which is out of scope for this build.
- **No Publisher-side Library Candidate nomination call.** PUBLISHER.md Section 9 says Publisher
  "may nominate new Library candidates." The `LibraryCandidate` object and its
  `submit_candidate`/`review_candidate` workflow are fully implemented in the Library repo and are
  directly constructible from Publisher (same field shapes, `SubmittedBy.PUBLISHER` is already a
  valid enum value there); this repo does not yet ship a `service.nominate_library_candidate()`
  convenience wrapper. Adding one is a small follow-up, deliberately deferred rather than rushed
  into this pass.
- **No Manager/Portal card generation.** Review packages and missing-item notices are structured
  objects ready for Manager to surface as Portal cards; this repo does not create those cards
  (System Relationship Matrix ownership: Manager/Portal, not Publisher).

## Explicitly out of scope for this build

- Intelligence interpretation logic (Repo Placement Plan: "Should not contain").
- Library truth ownership (Repo Placement Plan: "Should not contain").
- External send/submission logic (Repo Placement Plan: "Should not contain") — explicitly verified
  absent, see `MERGE_READINESS_REPORT.md` Section 5 and `tests/test_no_external_send.py`.
- Autonomous approval (Repo Placement Plan: "Should not contain") — explicitly verified absent.
- Deployment logic (Repo Placement Plan: "Should not contain").

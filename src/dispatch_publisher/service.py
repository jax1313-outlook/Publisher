"""
Publisher service surfaces, per DISPATCH_SHARED_OBJECT_CONTRACTS_v1.md Section 6:

    publisher.create_request(...)
    publisher.create_readiness_packet(req)
    publisher.pull_libraries(req)
    publisher.create_inventory(req)
    publisher.create_missing_notice(req)
    publisher.create_review_package(req)
    publisher.approve_review_package(id, approver_id)
    publisher.create_archive_handoff(review_id)
    publisher.create_visibility_package(req)
    publisher.create_pod_bundle(req)

No function in this module makes a network call, sends email, or contacts a customer, broker, or
government system. There is no import of a networking library anywhere in this repo — see
tests/test_no_external_send.py, which asserts that structurally rather than trusting convention.

Publisher may not approve itself (Hard Rule): `approve_review_package` is the only function that
can move a DraftReviewPackage to APPROVED_BY_MIKE, and it requires an `approver_id` that is not a
reserved system identity. `create_archive_handoff` refuses to run unless the referenced review is
already APPROVED_BY_MIKE — Publisher cannot hand its own unapproved drafts to Archive.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from dispatch_publisher.intelligence_client import requirement_types_present
from dispatch_publisher.library_client import MISSING, LibraryClient
from dispatch_publisher.models import (
    RESERVED_SYSTEM_IDENTITIES,
    ArchiveHandoffPackage,
    CompletenessStatus,
    DraftReviewPackage,
    EvidenceItem,
    ItemSource,
    ItemStatus,
    MissingItemNotice,
    PODEvidenceBundle,
    PartsInventory,
    PublisherRequest,
    ReadinessPacket,
    ReadinessStatus,
    RecipeType,
    RecipientType,
    RequiredItem,
    ReviewStatus,
    VisibilityPackage,
    Workspace,
)


def create_request(
    recipe_code: str,
    recipe_type: RecipeType,
    publisher_requirement_ids: Optional[List[str]] = None,
) -> PublisherRequest:
    return PublisherRequest(
        recipe_code=recipe_code,
        recipe_type=recipe_type,
        publisher_requirement_ids=list(publisher_requirement_ids or []),
    )


def pull_libraries(request: PublisherRequest, library_client: LibraryClient) -> Workspace:
    """publisher.pull_libraries() — resolve the request's recipe against Library.

    Never invents a resolution: an object_code the LibraryClient does not have is recorded as
    MISSING in `pending_parts`, not silently dropped or filled in.
    """
    resolved = library_client.resolve_packet(request.recipe_type.value)
    pulled: Dict[str, Any] = {}
    pending: List[str] = []
    for object_code, value in resolved.items():
        if value == MISSING or value is None:
            pending.append(object_code)
        else:
            pulled[object_code] = value

    return Workspace(request_id=request.request_id, pulled_library_objects=pulled, pending_parts=pending)


def create_readiness_packet(
    request: PublisherRequest,
    workspace: Workspace,
    intelligence_requirements: Optional[List[Any]] = None,
    required_intelligence_requirement_types: Optional[List[str]] = None,
) -> ReadinessPacket:
    """publisher.create_readiness_packet() — list every required item and whether it is present.

    Combines Library-sourced items (from the Workspace pull) with Intelligence-requirement-type
    items (from the supplied requirement list). Nothing here fabricates a PRESENT status for an
    item that was not actually resolved/ready.
    """
    required_items: List[RequiredItem] = []

    for object_code in workspace.pulled_library_objects:
        required_items.append(RequiredItem(object_code, ItemSource.LIBRARY, ItemStatus.PRESENT))
    for object_code in workspace.pending_parts:
        required_items.append(RequiredItem(object_code, ItemSource.LIBRARY, ItemStatus.MISSING))

    if required_intelligence_requirement_types:
        presence = requirement_types_present(
            intelligence_requirements or [], required_intelligence_requirement_types
        )
        for req_type, is_present in presence.items():
            status = ItemStatus.PRESENT if is_present else ItemStatus.MISSING
            required_items.append(RequiredItem(req_type, ItemSource.INTELLIGENCE, status))

    overall_status = (
        ReadinessStatus.READY
        if all(item.status == ItemStatus.PRESENT for item in required_items)
        else ReadinessStatus.INCOMPLETE
    )

    return ReadinessPacket(
        request_id=request.request_id,
        recipe_code=request.recipe_code,
        required_items=required_items,
        overall_status=overall_status,
    )


def create_inventory(readiness_packet: ReadinessPacket) -> PartsInventory:
    present = [item.item_code for item in readiness_packet.required_items if item.status == ItemStatus.PRESENT]
    missing = [item.item_code for item in readiness_packet.required_items if item.status == ItemStatus.MISSING]
    return PartsInventory(request_id=readiness_packet.request_id, present_items=present, missing_items=missing)


def create_missing_notice(inventory: PartsInventory) -> Optional[MissingItemNotice]:
    """publisher.create_missing_notice() — draft only, never sent.

    Returns None when nothing is missing — this function does not create a notice with an
    invented gap. `recipient_hint` defaults to an internal reviewer ("Mike"); the model layer
    rejects any customer/broker/government value.
    """
    if not inventory.missing_items:
        return None
    return MissingItemNotice(request_id=inventory.request_id, missing_items=list(inventory.missing_items))


def create_review_package(
    request: PublisherRequest,
    readiness_packet: ReadinessPacket,
    inventory: PartsInventory,
    missing_notice: Optional[MissingItemNotice] = None,
) -> DraftReviewPackage:
    status = ReviewStatus.REVIEW_READY if readiness_packet.overall_status == ReadinessStatus.READY else ReviewStatus.DRAFT
    summary = (
        f"Recipe {readiness_packet.recipe_code}: {len(inventory.present_items)} present, "
        f"{len(inventory.missing_items)} missing."
    )
    return DraftReviewPackage(
        request_id=request.request_id,
        readiness_packet_id=readiness_packet.packet_id,
        inventory_id=inventory.inventory_id,
        contents_summary=summary,
        missing_notice_id=missing_notice.notice_id if missing_notice else None,
        status=status,
    )


def approve_review_package(review: DraftReviewPackage, approver_id: str) -> DraftReviewPackage:
    """publisher.approve_review_package() — the ONLY path to APPROVED_BY_MIKE.

    Hard Rule: Publisher may not approve itself. `approver_id` must identify a real human/
    approved-workflow reviewer, never a system identity — enforced here, not by convention.
    """
    if review.status in (ReviewStatus.APPROVED_BY_MIKE, ReviewStatus.REJECTED):
        raise ValueError(f"review {review.review_id!r} already finalized (status={review.status})")
    if not approver_id or approver_id.strip().upper() in RESERVED_SYSTEM_IDENTITIES:
        raise ValueError(
            "approver_id must identify a real human or approved-workflow reviewer, not a system "
            "identity (Hard Rule: Publisher may not approve itself)"
        )

    from dispatch_publisher.models import _now

    review.approved_by = approver_id
    review.approved_at = _now()
    review.status = ReviewStatus.APPROVED_BY_MIKE
    return review


def reject_review_package(review: DraftReviewPackage, reviewer_id: str) -> DraftReviewPackage:
    if review.status in (ReviewStatus.APPROVED_BY_MIKE, ReviewStatus.REJECTED):
        raise ValueError(f"review {review.review_id!r} already finalized (status={review.status})")
    if not reviewer_id or reviewer_id.strip().upper() in RESERVED_SYSTEM_IDENTITIES:
        raise ValueError("reviewer_id must identify a real human or approved-workflow reviewer")

    from dispatch_publisher.models import _now

    review.approved_by = reviewer_id
    review.approved_at = _now()
    review.status = ReviewStatus.REJECTED
    return review


def create_archive_handoff(review: DraftReviewPackage) -> ArchiveHandoffPackage:
    """publisher.create_archive_handoff() — blocked unless the review is human-approved.

    Hard Rule: Publisher may not submit its own unapproved drafts to Archive as if final.
    """
    if review.status != ReviewStatus.APPROVED_BY_MIKE:
        raise ValueError(
            f"cannot create Archive handoff for review {review.review_id!r}: "
            f"status is {review.status}, not APPROVED_BY_MIKE"
        )
    manifest = [review.review_id, review.readiness_packet_id, review.inventory_id]
    if review.missing_notice_id:
        manifest.append(review.missing_notice_id)
    return ArchiveHandoffPackage(review_id=review.review_id, bundle_manifest=manifest)


def create_visibility_package(
    request: PublisherRequest,
    load_or_shipment_ref: str,
    status_snapshot: Dict[str, Any],
    intended_recipient_type: RecipientType,
    pod_reference: Optional[str] = None,
) -> VisibilityPackage:
    """publisher.create_visibility_package() — M1 scaffold, draft only, never sent.

    `send_status` is fixed NOT_SENT by the model layer; no code path in this repo can change it.
    Unknown status fields must be marked "UNKNOWN" by the caller, not silently omitted.
    """
    return VisibilityPackage(
        request_id=request.request_id,
        load_or_shipment_ref=load_or_shipment_ref,
        status_snapshot=dict(status_snapshot),
        intended_recipient_type=intended_recipient_type,
        pod_reference=pod_reference,
    )


def create_pod_bundle(request: PublisherRequest, evidence_items: List[EvidenceItem]) -> PODEvidenceBundle:
    completeness = (
        CompletenessStatus.COMPLETE
        if evidence_items and all(item.status == ItemStatus.PRESENT for item in evidence_items)
        else CompletenessStatus.INCOMPLETE
    )
    return PODEvidenceBundle(
        request_id=request.request_id, evidence_items=list(evidence_items), completeness_status=completeness
    )

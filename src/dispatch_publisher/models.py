"""
Object model for the Publisher department.

Schemas here MUST match DISPATCH_SHARED_OBJECT_CONTRACTS_v1.md (Claude-3 repo), Section 5,
field-for-field. Publisher is the last link in Intelligence -> Library -> Publisher: it consumes
objects from both upstream repos (via the client interfaces in library_client.py /
intelligence_client.py) but owns nothing that becomes truth by itself.

Hard Rules enforced structurally in this module (not just by convention):
  - No object here has a field for an outbound customer/broker/government contact channel.
  - DraftReviewPackage.status can only reach APPROVED_BY_MIKE through service.approve_review_package,
    which requires an external approver_id (see service.py). No constructor argument sets it directly
    to APPROVED_BY_MIKE.
  - VisibilityPackage.send_status and PODEvidenceBundle have no "SENT" state anywhere in this repo.
"""
from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _asdict(obj: Any) -> Dict[str, Any]:
    def _convert(value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, list):
            return [_convert(v) for v in value]
        if isinstance(value, dict):
            return {k: _convert(v) for k, v in value.items()}
        if dataclasses.is_dataclass(value):
            return _asdict(value)
        return value

    return {f.name: _convert(getattr(obj, f.name)) for f in dataclasses.fields(obj)}


class RecipeType(str, Enum):
    BROKER_ONBOARDING_PACKET = "BROKER_ONBOARDING_PACKET"
    GOVERNMENT_PROPOSAL_PACKET = "GOVERNMENT_PROPOSAL_PACKET"
    VISIBILITY_STATUS_PACKET = "VISIBILITY_STATUS_PACKET"
    POD_PACKAGE = "POD_PACKAGE"
    REVIEW_PACKAGE = "REVIEW_PACKAGE"


class RequestStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"


class ItemSource(str, Enum):
    LIBRARY = "LIBRARY"
    PARTS = "PARTS"
    INTELLIGENCE = "INTELLIGENCE"


class ItemStatus(str, Enum):
    PRESENT = "PRESENT"
    MISSING = "MISSING"


class ReadinessStatus(str, Enum):
    READY = "READY"
    INCOMPLETE = "INCOMPLETE"


class ReviewStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEW_READY = "REVIEW_READY"
    NEEDS_MIKE_DECISION = "NEEDS_MIKE_DECISION"
    APPROVED_BY_MIKE = "APPROVED_BY_MIKE"
    REJECTED = "REJECTED"


class CompletenessStatus(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


class RecipientType(str, Enum):
    CUSTOMER = "CUSTOMER"
    BROKER = "BROKER"


# Identities that may never be used as an approver — Publisher may not approve itself.
RESERVED_SYSTEM_IDENTITIES = {"PUBLISHER", "INTELLIGENCE", "LIBRARY", "SYSTEM", "AUTOMATION"}


@dataclasses.dataclass
class RequiredItem:
    item_code: str
    source: ItemSource
    status: ItemStatus

    def to_dict(self) -> Dict[str, Any]:
        return _asdict(self)


@dataclasses.dataclass
class PublisherRequest:
    recipe_code: str
    recipe_type: RecipeType
    publisher_requirement_ids: List[str] = dataclasses.field(default_factory=list)
    workspace_id: Optional[str] = None
    status: RequestStatus = RequestStatus.OPEN
    request_id: str = dataclasses.field(default_factory=_new_id)
    created_at: str = dataclasses.field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _asdict(self)


@dataclasses.dataclass
class Workspace:
    request_id: str
    pulled_library_objects: Dict[str, Any] = dataclasses.field(default_factory=dict)
    pending_parts: List[str] = dataclasses.field(default_factory=list)
    notes: str = ""
    workspace_id: str = dataclasses.field(default_factory=_new_id)
    created_at: str = dataclasses.field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _asdict(self)


@dataclasses.dataclass
class ReadinessPacket:
    request_id: str
    recipe_code: str
    required_items: List[RequiredItem]
    overall_status: ReadinessStatus
    packet_id: str = dataclasses.field(default_factory=_new_id)
    created_at: str = dataclasses.field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _asdict(self)


@dataclasses.dataclass
class PartsInventory:
    request_id: str
    present_items: List[str]
    missing_items: List[str]
    inventory_id: str = dataclasses.field(default_factory=_new_id)
    generated_at: str = dataclasses.field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _asdict(self)


@dataclasses.dataclass
class MissingItemNotice:
    request_id: str
    missing_items: List[str]
    recipient_hint: str = "Mike"
    status: str = dataclasses.field(default="DRAFT", init=False)
    notice_id: str = dataclasses.field(default_factory=_new_id)
    drafted_at: str = dataclasses.field(default_factory=_now)

    def __post_init__(self) -> None:
        if self.recipient_hint.strip().upper() in {"CUSTOMER", "BROKER", "GOVERNMENT", "AGENCY"}:
            raise ValueError(
                "recipient_hint must be an internal recipient (e.g. 'Mike'), never a "
                "customer/broker/government identity (Hard Rule: no autonomous external communication)"
            )

    def to_dict(self) -> Dict[str, Any]:
        return _asdict(self)


@dataclasses.dataclass
class DraftReviewPackage:
    request_id: str
    readiness_packet_id: str
    inventory_id: str
    contents_summary: str
    missing_notice_id: Optional[str] = None
    status: ReviewStatus = ReviewStatus.DRAFT
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    review_id: str = dataclasses.field(default_factory=_new_id)
    created_at: str = dataclasses.field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _asdict(self)


@dataclasses.dataclass
class ArchiveHandoffPackage:
    review_id: str
    bundle_manifest: List[str]
    retention_class: str = "STANDARD"
    handoff_id: str = dataclasses.field(default_factory=_new_id)
    created_at: str = dataclasses.field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _asdict(self)


@dataclasses.dataclass
class VisibilityPackage:
    request_id: str
    load_or_shipment_ref: str
    status_snapshot: Dict[str, Any]
    intended_recipient_type: RecipientType
    pod_reference: Optional[str] = None
    send_status: str = dataclasses.field(default="NOT_SENT", init=False)
    visibility_id: str = dataclasses.field(default_factory=_new_id)
    generated_at: str = dataclasses.field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _asdict(self)


@dataclasses.dataclass
class EvidenceItem:
    item_code: str
    source_ref: str
    status: ItemStatus

    def to_dict(self) -> Dict[str, Any]:
        return _asdict(self)


@dataclasses.dataclass
class PODEvidenceBundle:
    request_id: str
    evidence_items: List[EvidenceItem]
    completeness_status: CompletenessStatus
    bundle_id: str = dataclasses.field(default_factory=_new_id)
    generated_at: str = dataclasses.field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _asdict(self)

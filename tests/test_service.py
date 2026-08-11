import pytest

from dispatch_publisher import service
from dispatch_publisher.intelligence_client import requirement_types_present
from dispatch_publisher.library_client import StubLibraryClient
from dispatch_publisher.models import (
    EvidenceItem,
    ItemStatus,
    ReadinessStatus,
    RecipeType,
    RecipientType,
    ReviewStatus,
)


class _FakeRequirement:
    def __init__(self, requirement_type, status):
        self.requirement_type = requirement_type
        self.status = status


def _library_with(objects=None, required_codes=None):
    client = StubLibraryClient()
    client.put_recipe(
        RecipeType.BROKER_ONBOARDING_PACKET.value,
        {"required_library_object_codes": required_codes or []},
    )
    for code, obj in (objects or {}).items():
        client.put_object(code, obj)
    return client


def test_pull_libraries_reports_missing_not_fabricated():
    client = _library_with(required_codes=["W9-TEMPLATE", "COI-TEMPLATE"])
    request = service.create_request("RECIPE-1", RecipeType.BROKER_ONBOARDING_PACKET)

    workspace = service.pull_libraries(request, client)
    assert workspace.pulled_library_objects == {}
    assert set(workspace.pending_parts) == {"W9-TEMPLATE", "COI-TEMPLATE"}


def test_pull_libraries_picks_up_present_objects():
    client = _library_with(objects={"W9-TEMPLATE": {"title": "W9"}}, required_codes=["W9-TEMPLATE", "COI-TEMPLATE"])
    request = service.create_request("RECIPE-1", RecipeType.BROKER_ONBOARDING_PACKET)

    workspace = service.pull_libraries(request, client)
    assert "W9-TEMPLATE" in workspace.pulled_library_objects
    assert workspace.pending_parts == ["COI-TEMPLATE"]


def test_readiness_packet_lists_all_required_items():
    client = _library_with(objects={"W9-TEMPLATE": {"title": "W9"}}, required_codes=["W9-TEMPLATE", "COI-TEMPLATE"])
    request = service.create_request("RECIPE-1", RecipeType.BROKER_ONBOARDING_PACKET)
    workspace = service.pull_libraries(request, client)

    packet = service.create_readiness_packet(request, workspace)
    codes = {item.item_code for item in packet.required_items}
    assert codes == {"W9-TEMPLATE", "COI-TEMPLATE"}
    assert packet.overall_status == ReadinessStatus.INCOMPLETE


def test_readiness_packet_ready_when_all_present():
    client = _library_with(objects={"W9-TEMPLATE": {"title": "W9"}}, required_codes=["W9-TEMPLATE"])
    request = service.create_request("RECIPE-1", RecipeType.BROKER_ONBOARDING_PACKET)
    workspace = service.pull_libraries(request, client)

    packet = service.create_readiness_packet(request, workspace)
    assert packet.overall_status == ReadinessStatus.READY


def test_readiness_packet_includes_intelligence_requirement_types():
    client = _library_with(required_codes=[])
    request = service.create_request("RECIPE-1", RecipeType.BROKER_ONBOARDING_PACKET)
    workspace = service.pull_libraries(request, client)

    requirements = [_FakeRequirement("FORM", "READY"), _FakeRequirement("CERTIFICATION", "NEEDS_SOURCE")]
    packet = service.create_readiness_packet(
        request, workspace,
        intelligence_requirements=requirements,
        required_intelligence_requirement_types=["FORM", "CERTIFICATION"],
    )
    by_code = {item.item_code: item.status for item in packet.required_items}
    assert by_code["FORM"] == ItemStatus.PRESENT
    assert by_code["CERTIFICATION"] == ItemStatus.MISSING
    assert packet.overall_status == ReadinessStatus.INCOMPLETE


def test_inventory_and_missing_notice_gaps_visible():
    client = _library_with(required_codes=["W9-TEMPLATE", "COI-TEMPLATE"])
    request = service.create_request("RECIPE-1", RecipeType.BROKER_ONBOARDING_PACKET)
    workspace = service.pull_libraries(request, client)
    packet = service.create_readiness_packet(request, workspace)
    inventory = service.create_inventory(packet)

    assert set(inventory.missing_items) == {"W9-TEMPLATE", "COI-TEMPLATE"}

    notice = service.create_missing_notice(inventory)
    assert notice is not None
    assert set(notice.missing_items) == {"W9-TEMPLATE", "COI-TEMPLATE"}
    assert notice.status == "DRAFT"
    assert notice.recipient_hint == "Mike"


def test_missing_notice_none_when_nothing_missing():
    client = _library_with(objects={"W9-TEMPLATE": {"t": 1}}, required_codes=["W9-TEMPLATE"])
    request = service.create_request("RECIPE-1", RecipeType.BROKER_ONBOARDING_PACKET)
    workspace = service.pull_libraries(request, client)
    packet = service.create_readiness_packet(request, workspace)
    inventory = service.create_inventory(packet)

    assert service.create_missing_notice(inventory) is None


def test_review_package_cannot_approve_itself():
    client = _library_with(objects={"W9-TEMPLATE": {"t": 1}}, required_codes=["W9-TEMPLATE"])
    request = service.create_request("RECIPE-1", RecipeType.BROKER_ONBOARDING_PACKET)
    workspace = service.pull_libraries(request, client)
    packet = service.create_readiness_packet(request, workspace)
    inventory = service.create_inventory(packet)
    review = service.create_review_package(request, packet, inventory)

    assert review.status == ReviewStatus.REVIEW_READY

    with pytest.raises(ValueError):
        service.approve_review_package(review, "PUBLISHER")
    with pytest.raises(ValueError):
        service.approve_review_package(review, "")


def test_review_package_approval_requires_external_human():
    client = _library_with(objects={"W9-TEMPLATE": {"t": 1}}, required_codes=["W9-TEMPLATE"])
    request = service.create_request("RECIPE-1", RecipeType.BROKER_ONBOARDING_PACKET)
    workspace = service.pull_libraries(request, client)
    packet = service.create_readiness_packet(request, workspace)
    inventory = service.create_inventory(packet)
    review = service.create_review_package(request, packet, inventory)

    approved = service.approve_review_package(review, "Mike Zachary")
    assert approved.status == ReviewStatus.APPROVED_BY_MIKE
    assert approved.approved_by == "Mike Zachary"

    with pytest.raises(ValueError):
        service.approve_review_package(review, "Mike Zachary")


def test_archive_handoff_blocked_without_approval():
    client = _library_with(objects={"W9-TEMPLATE": {"t": 1}}, required_codes=["W9-TEMPLATE"])
    request = service.create_request("RECIPE-1", RecipeType.BROKER_ONBOARDING_PACKET)
    workspace = service.pull_libraries(request, client)
    packet = service.create_readiness_packet(request, workspace)
    inventory = service.create_inventory(packet)
    review = service.create_review_package(request, packet, inventory)

    with pytest.raises(ValueError):
        service.create_archive_handoff(review)

    service.approve_review_package(review, "Mike Zachary")
    handoff = service.create_archive_handoff(review)
    assert review.review_id in handoff.bundle_manifest


def test_visibility_package_never_sent():
    request = service.create_request("RECIPE-2", RecipeType.VISIBILITY_STATUS_PACKET)
    package = service.create_visibility_package(
        request,
        load_or_shipment_ref="LOAD-123",
        status_snapshot={"location": "UNKNOWN"},
        intended_recipient_type=RecipientType.BROKER,
    )
    assert package.send_status == "NOT_SENT"


def test_pod_bundle_completeness_reflects_missing_evidence():
    request = service.create_request("RECIPE-3", RecipeType.POD_PACKAGE)
    bundle = service.create_pod_bundle(
        request,
        [
            EvidenceItem("POD_PHOTO", "source-1", ItemStatus.PRESENT),
            EvidenceItem("SIGNATURE", "source-2", ItemStatus.MISSING),
        ],
    )
    assert bundle.completeness_status.value == "INCOMPLETE"


def test_requirement_types_present_does_not_fabricate():
    requirements = [_FakeRequirement("FORM", "READY")]
    result = requirement_types_present(requirements, ["FORM", "CERTIFICATION"])
    assert result == {"FORM": True, "CERTIFICATION": False}

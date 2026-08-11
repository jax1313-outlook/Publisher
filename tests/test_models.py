import pytest

from dispatch_publisher.models import MissingItemNotice, VisibilityPackage, RecipientType


def test_missing_item_notice_rejects_external_recipient_hint():
    with pytest.raises(ValueError):
        MissingItemNotice(request_id="req-1", missing_items=["X"], recipient_hint="Customer")
    with pytest.raises(ValueError):
        MissingItemNotice(request_id="req-1", missing_items=["X"], recipient_hint="Broker")
    with pytest.raises(ValueError):
        MissingItemNotice(request_id="req-1", missing_items=["X"], recipient_hint="Government")


def test_missing_item_notice_accepts_internal_recipient():
    notice = MissingItemNotice(request_id="req-1", missing_items=["X"], recipient_hint="Mike")
    assert notice.status == "DRAFT"


def test_visibility_package_send_status_not_a_constructor_argument():
    package = VisibilityPackage(
        request_id="req-1",
        load_or_shipment_ref="LOAD-1",
        status_snapshot={},
        intended_recipient_type=RecipientType.CUSTOMER,
    )
    assert package.send_status == "NOT_SENT"

    with pytest.raises(TypeError):
        VisibilityPackage(
            request_id="req-1",
            load_or_shipment_ref="LOAD-1",
            status_snapshot={},
            intended_recipient_type=RecipientType.CUSTOMER,
            send_status="SENT",
        )

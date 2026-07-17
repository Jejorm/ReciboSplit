"""Unit tests for db.create_receipt() -- the "payer must be a participant of
this event" application-level invariant (the schema FK only guarantees the
payer is *some* participant, not one linked to the receipt's event)."""

import pytest


def test_payer_not_linked_to_event_rejected(local_db):
    ana_id = local_db.create_participant("Ana")
    event_id = local_db.create_event("Solo event")
    # Ana is NOT added to the event via add_participant_to_event().
    with pytest.raises(ValueError, match="not a participant of"):
        local_db.create_receipt(event_id, ana_id, 50.0, "uploads/fake.png")


def test_payer_linked_to_event_passes(local_db):
    ana_id = local_db.create_participant("Ana")
    event_id = local_db.create_event("Solo event")
    local_db.add_participant_to_event(event_id, ana_id)

    receipt_id = local_db.create_receipt(event_id, ana_id, 50.0, "uploads/fake.png")

    receipt = local_db.get_receipt_with_items(receipt_id)
    assert receipt is not None
    assert receipt["paid_by"] == ana_id
    assert receipt["total_amount"] == 50.0
    assert receipt["event_id"] == event_id


def test_receipt_for_nonexistent_event_rejected(local_db):
    ana_id = local_db.create_participant("Ana")
    with pytest.raises(ValueError, match="does not exist"):
        local_db.create_receipt(999999, ana_id, 50.0, "uploads/fake.png")


def test_receipt_with_nonexistent_payer_rejected(local_db):
    event_id = local_db.create_event("Solo event")
    with pytest.raises(ValueError, match="does not exist"):
        local_db.create_receipt(event_id, 999999, 50.0, "uploads/fake.png")

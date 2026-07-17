"""Unit tests for db.delete_participant()'s safe-deletion policy: refuse if
the participant carries financial history (paid a receipt or holds an item
assignment), otherwise cascade-delete their event_participants links and
succeed."""

import pytest


def test_refuses_when_participant_has_paid_a_receipt(local_db):
    ana_id = local_db.create_participant("Ana")
    event_id = local_db.create_event("Event")
    local_db.add_participant_to_event(event_id, ana_id)
    local_db.create_receipt(event_id, ana_id, 30.0, "uploads/fake.png")

    with pytest.raises(ValueError, match="paid for one or more receipts"):
        local_db.delete_participant(ana_id)

    # Must not have been deleted.
    assert any(p["id"] == ana_id for p in local_db.list_participants())


def test_refuses_when_participant_has_an_item_assignment(local_db):
    ana_id = local_db.create_participant("Ana")
    bruno_id = local_db.create_participant("Bruno")
    event_id = local_db.create_event("Event")
    local_db.add_participant_to_event(event_id, ana_id)
    local_db.add_participant_to_event(event_id, bruno_id)

    receipt_id = local_db.create_receipt(event_id, ana_id, 30.0, "uploads/fake.png")
    item_id = local_db.add_item(receipt_id, "Item", 30.0)
    local_db.assign_item(item_id, [{"participant_id": bruno_id, "share": 1.0}])

    # Bruno never paid anything, but he does consume this item.
    with pytest.raises(ValueError, match="item assignments"):
        local_db.delete_participant(bruno_id)

    assert any(p["id"] == bruno_id for p in local_db.list_participants())


def test_succeeds_without_financial_history(local_db):
    ana_id = local_db.create_participant("Ana")
    event_id = local_db.create_event("Event")
    local_db.add_participant_to_event(event_id, ana_id)

    # Ana is linked to the event but has no receipts or assignments.
    local_db.delete_participant(ana_id)

    assert not any(p["id"] == ana_id for p in local_db.list_participants())


def test_nonexistent_participant_rejected(local_db):
    with pytest.raises(ValueError, match="does not exist"):
        local_db.delete_participant(999999)

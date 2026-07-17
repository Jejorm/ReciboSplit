"""Unit tests for db.assign_item() -- replace-semantics assignment writes,
and the invariants it enforces beyond validate_shares() (duplicate
participants, share > 0, participant must belong to the item's event,
item must exist)."""

import pytest


@pytest.fixture
def scenario(local_db):
    """Two participants (Ana, Bruno) linked to one event, one receipt paid
    by Ana, one item on that receipt. A third participant (Carla) exists but
    is NOT linked to the event -- used by the "participant not in event"
    test."""
    ana_id = local_db.create_participant("Ana")
    bruno_id = local_db.create_participant("Bruno")
    carla_id = local_db.create_participant("Carla")  # not linked to the event

    event_id = local_db.create_event("Test event")
    local_db.add_participant_to_event(event_id, ana_id)
    local_db.add_participant_to_event(event_id, bruno_id)

    receipt_id = local_db.create_receipt(event_id, ana_id, 20.0, "uploads/fake.png")
    item_id = local_db.add_item(receipt_id, "Item", 20.0)

    return {
        "ana_id": ana_id,
        "bruno_id": bruno_id,
        "carla_id": carla_id,
        "event_id": event_id,
        "item_id": item_id,
    }


def test_happy_path_assigns_and_is_readable(local_db, scenario):
    local_db.assign_item(
        scenario["item_id"],
        [
            {"participant_id": scenario["ana_id"], "share": 0.5},
            {"participant_id": scenario["bruno_id"], "share": 0.5},
        ],
    )
    assignments = local_db.get_item_assignments(scenario["item_id"])
    assert len(assignments) == 2
    shares_by_name = {a["participant_name"]: a["share"] for a in assignments}
    assert shares_by_name == {"Ana": 0.5, "Bruno": 0.5}


def test_second_call_fully_replaces_the_first(local_db, scenario):
    local_db.assign_item(
        scenario["item_id"],
        [
            {"participant_id": scenario["ana_id"], "share": 0.5},
            {"participant_id": scenario["bruno_id"], "share": 0.5},
        ],
    )
    # Second call assigns the whole item to Ana alone -- must fully supersede
    # the first, not merge with it.
    local_db.assign_item(
        scenario["item_id"],
        [{"participant_id": scenario["ana_id"], "share": 1.0}],
    )
    assignments = local_db.get_item_assignments(scenario["item_id"])
    assert len(assignments) == 1
    assert assignments[0]["participant_name"] == "Ana"
    assert assignments[0]["share"] == 1.0


def test_duplicate_participant_rejected(local_db, scenario):
    with pytest.raises(ValueError, match="Duplicate participant"):
        local_db.assign_item(
            scenario["item_id"],
            [
                {"participant_id": scenario["ana_id"], "share": 0.5},
                {"participant_id": scenario["ana_id"], "share": 0.5},
            ],
        )


@pytest.mark.parametrize("bad_share", [0, -0.5])
def test_share_not_greater_than_zero_rejected(local_db, scenario, bad_share):
    with pytest.raises(ValueError, match="must be"):
        local_db.assign_item(
            scenario["item_id"],
            [
                {"participant_id": scenario["ana_id"], "share": bad_share},
                {"participant_id": scenario["bruno_id"], "share": 1 - bad_share},
            ],
        )


def test_participant_not_in_event_rejected(local_db, scenario):
    # Carla exists but was never added to this event.
    with pytest.raises(ValueError, match="not a participant of event"):
        local_db.assign_item(
            scenario["item_id"],
            [
                {"participant_id": scenario["ana_id"], "share": 0.5},
                {"participant_id": scenario["carla_id"], "share": 0.5},
            ],
        )


def test_nonexistent_item_rejected(local_db, scenario):
    with pytest.raises(ValueError, match="does not exist"):
        local_db.assign_item(
            999999,
            [{"participant_id": scenario["ana_id"], "share": 1.0}],
        )


def test_empty_assignments_rejected(local_db, scenario):
    with pytest.raises(ValueError, match="At least one assignment"):
        local_db.assign_item(scenario["item_id"], [])


def test_shares_not_summing_to_one_rejected(local_db, scenario):
    with pytest.raises(ValueError, match="must sum to 1.0"):
        local_db.assign_item(
            scenario["item_id"],
            [
                {"participant_id": scenario["ana_id"], "share": 0.5},
                {"participant_id": scenario["bruno_id"], "share": 0.4},
            ],
        )

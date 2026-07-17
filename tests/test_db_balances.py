"""Core balance-calculation tests: db.get_event_balances() and
db.get_overall_balances(), which are plain SELECTs over schema.sql's
event_balances / overall_balances views (CLAUDE.md: balance math lives only
in SQL, never duplicated here or in the frontend).

The main scenario below recreates the Phase 1 acceptance scenario from
PROJECT_STATUS.md's "Definition of Done" table exactly, via db.py's public
functions (never raw SQL), and asserts the exact expected numbers."""

import pytest


@pytest.fixture
def acceptance_scenario(local_db):
    """Builds the full Phase 1 acceptance scenario:

    Event 1 "Asado sabado" -- Ana, Bruno, Carla
      Receipt paid by Ana, total $90
        - Carne $60, split evenly among Ana/Bruno/Carla (1/3 each)
        - Bebidas $30, split evenly between Bruno/Carla only (1/2 each)

    Event 2 "Dia de playa" -- Bruno, Carla (Ana not included)
      Receipt paid by Carla, total $40
        - Snacks $40, split evenly between Bruno/Carla (1/2 each)
    """
    db = local_db

    ana_id = db.create_participant("Ana")
    bruno_id = db.create_participant("Bruno")
    carla_id = db.create_participant("Carla")

    event1_id = db.create_event("Asado sabado")
    db.add_participant_to_event(event1_id, ana_id)
    db.add_participant_to_event(event1_id, bruno_id)
    db.add_participant_to_event(event1_id, carla_id)

    receipt1_id = db.create_receipt(event1_id, ana_id, 90.0, "uploads/receipt1.png")
    carne_id = db.add_item(receipt1_id, "Carne", 60.0)
    db.assign_item(
        carne_id,
        [
            {"participant_id": ana_id, "share": 1 / 3},
            {"participant_id": bruno_id, "share": 1 / 3},
            {"participant_id": carla_id, "share": 1 / 3},
        ],
    )
    bebidas_id = db.add_item(receipt1_id, "Bebidas", 30.0)
    db.assign_item(
        bebidas_id,
        [
            {"participant_id": bruno_id, "share": 0.5},
            {"participant_id": carla_id, "share": 0.5},
        ],
    )

    event2_id = db.create_event("Dia de playa")
    db.add_participant_to_event(event2_id, bruno_id)
    db.add_participant_to_event(event2_id, carla_id)

    receipt2_id = db.create_receipt(event2_id, carla_id, 40.0, "uploads/receipt2.png")
    snacks_id = db.add_item(receipt2_id, "Snacks", 40.0)
    db.assign_item(
        snacks_id,
        [
            {"participant_id": bruno_id, "share": 0.5},
            {"participant_id": carla_id, "share": 0.5},
        ],
    )

    return {
        "ana_id": ana_id,
        "bruno_id": bruno_id,
        "carla_id": carla_id,
        "event1_id": event1_id,
        "event2_id": event2_id,
    }


def _by_name(balances: list[dict]) -> dict:
    return {row["participant_name"]: row for row in balances}


def test_event1_balances_exact(local_db, acceptance_scenario):
    balances = _by_name(local_db.get_event_balances(acceptance_scenario["event1_id"]))

    assert balances["Ana"]["total_paid"] == 90.0
    assert balances["Ana"]["total_consumed"] == pytest.approx(20.0)
    assert balances["Ana"]["net_balance"] == pytest.approx(70.0)

    assert balances["Bruno"]["total_paid"] == 0.0
    assert balances["Bruno"]["total_consumed"] == pytest.approx(35.0)
    assert balances["Bruno"]["net_balance"] == pytest.approx(-35.0)

    assert balances["Carla"]["total_paid"] == 0.0
    assert balances["Carla"]["total_consumed"] == pytest.approx(35.0)
    assert balances["Carla"]["net_balance"] == pytest.approx(-35.0)


def test_event2_balances_exact(local_db, acceptance_scenario):
    balances = _by_name(local_db.get_event_balances(acceptance_scenario["event2_id"]))

    # Ana is not a participant of event 2 -- must not appear at all.
    assert "Ana" not in balances

    assert balances["Bruno"]["total_paid"] == 0.0
    assert balances["Bruno"]["total_consumed"] == pytest.approx(20.0)
    assert balances["Bruno"]["net_balance"] == pytest.approx(-20.0)

    assert balances["Carla"]["total_paid"] == 40.0
    assert balances["Carla"]["total_consumed"] == pytest.approx(20.0)
    assert balances["Carla"]["net_balance"] == pytest.approx(20.0)


def test_overall_balances_exact(local_db, acceptance_scenario):
    balances = _by_name(local_db.get_overall_balances())

    assert balances["Ana"]["total_paid_all_events"] == 90.0
    assert balances["Ana"]["total_consumed_all_events"] == pytest.approx(20.0)
    assert balances["Ana"]["total_net_balance"] == pytest.approx(70.0)

    assert balances["Bruno"]["total_paid_all_events"] == 0.0
    assert balances["Bruno"]["total_consumed_all_events"] == pytest.approx(55.0)
    assert balances["Bruno"]["total_net_balance"] == pytest.approx(-55.0)

    assert balances["Carla"]["total_paid_all_events"] == 40.0
    assert balances["Carla"]["total_consumed_all_events"] == pytest.approx(55.0)
    assert balances["Carla"]["total_net_balance"] == pytest.approx(-15.0)

    net_sum = sum(row["total_net_balance"] for row in balances.values())
    assert net_sum == pytest.approx(0.0, abs=1e-9)


# --- Edge cases ---------------------------------------------------------------


def test_event_with_participants_but_no_receipts(local_db):
    """An event with participants linked but zero receipts still returns one
    row per participant, all zeroed out via the view's COALESCE -- it is NOT
    an empty result set. This documents the actual event_balances behavior
    per db.get_event_balances()'s docstring."""
    ana_id = local_db.create_participant("Ana")
    bruno_id = local_db.create_participant("Bruno")
    event_id = local_db.create_event("Empty event")
    local_db.add_participant_to_event(event_id, ana_id)
    local_db.add_participant_to_event(event_id, bruno_id)

    balances = local_db.get_event_balances(event_id)

    assert len(balances) == 2
    for row in balances:
        assert row["total_paid"] == 0.0
        assert row["total_consumed"] == 0.0
        assert row["net_balance"] == 0.0


def test_get_event_balances_on_nonexistent_event_raises(local_db):
    with pytest.raises(ValueError, match="does not exist"):
        local_db.get_event_balances(999999)


def test_overall_balances_excludes_participants_with_no_event_history(local_db):
    """A participant who exists but was never linked to any event via
    event_participants has no event_balances rows at all, so they are
    absent from overall_balances -- not present with zeros. Documents the
    behavior noted in db.get_overall_balances()'s docstring."""
    local_db.create_participant("Lonely")

    balances = _by_name(local_db.get_overall_balances())
    assert "Lonely" not in balances

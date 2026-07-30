"""Unit tests for the events.currency column (display-only, no conversion --
see schema.sql / migrations/0001_add_event_currency.sql): create_event()'s
default/override, list_events()/get_event_with_participants() exposing it,
and update_event_currency()."""

import pytest


def test_create_event_defaults_to_usd(local_db):
    event_id = local_db.create_event("Asado")

    event = local_db.get_event_with_participants(event_id)
    assert event["currency"] == "USD"


def test_create_event_with_explicit_currency(local_db):
    event_id = local_db.create_event("Viaje a Brasil", currency="BRL")

    event = local_db.get_event_with_participants(event_id)
    assert event["currency"] == "BRL"


def test_list_events_includes_currency(local_db):
    local_db.create_event("Asado", currency="ARS")

    events = local_db.list_events()
    assert len(events) == 1
    assert events[0]["currency"] == "ARS"


def test_update_event_currency(local_db):
    event_id = local_db.create_event("Asado")
    assert local_db.get_event_with_participants(event_id)["currency"] == "USD"

    local_db.update_event_currency(event_id, "ARS")

    event = local_db.get_event_with_participants(event_id)
    assert event["currency"] == "ARS"


def test_update_event_currency_nonexistent_event_rejected(local_db):
    with pytest.raises(ValueError, match="does not exist"):
        local_db.update_event_currency(999999, "ARS")

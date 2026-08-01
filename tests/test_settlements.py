"""Integration tests for settlements (cash payments between participants
that reduce debts within an event): POST/GET/DELETE /events/{id}/settlements,
GET /settlements, DELETE /settlements/{id}, and their effect on the
event_balances / overall_balances views (total_settled_sent,
total_settled_received, net_balance = paid - consumed + sent - received).

These deliberately do NOT repeat db-layer unit tests -- there are no
test_db_settlements.py-style tests yet for db.create_settlement's own
validation, so the validation-failure cases below double as the only
coverage for those invariants, exercised through the HTTP wiring
(services.value_error_to_http: "does not exist" -> 404, everything else ->
422), matching the convention in test_api_errors.py."""

import pytest


def _create_participant(client, name: str) -> int:
    response = client.post("/participants", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _create_event(client, name: str) -> int:
    response = client.post("/events", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _link(client, event_id: int, participant_id: int) -> None:
    response = client.post(
        f"/events/{event_id}/participants", json={"participant_id": participant_id}
    )
    assert response.status_code == 201


def _upload_receipt(client, event_id: int, payer_id: int, total: float, image_upload_files) -> int:
    response = client.post(
        f"/events/{event_id}/receipts",
        data={"payer_participant_id": payer_id, "total": total},
        files=image_upload_files(),
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_item(client, receipt_id: int, name: str, price: float) -> int:
    response = client.post(
        f"/receipts/{receipt_id}/items", json={"name": name, "price": price}
    )
    assert response.status_code == 201
    return response.json()[0]["id"]


def _assign(client, item_id: int, assignments: list[dict]) -> None:
    response = client.put(f"/items/{item_id}/assignments", json=assignments)
    assert response.status_code == 200


def _settle(
    client,
    event_id: int,
    from_id: int,
    to_id: int,
    amount: float,
    note: str | None = None,
) -> int:
    payload = {"from_participant_id": from_id, "to_participant_id": to_id, "amount": amount}
    if note is not None:
        payload["note"] = note
    response = client.post(f"/events/{event_id}/settlements", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def _event_balances_by_name(client, event_id: int) -> dict:
    return {row["participant_name"]: row for row in client.get(f"/events/{event_id}/balances").json()}


def _overall_balances_by_name(client) -> dict:
    return {row["participant_name"]: row for row in client.get("/balances").json()}


# --- Happy path -----------------------------------------------------------------


def test_create_settlement_returns_201_and_appears_in_event_list(api_client):
    client = api_client

    ana_id = _create_participant(client, "Ana")
    bruno_id = _create_participant(client, "Bruno")
    event_id = _create_event(client, "Cumple")
    _link(client, event_id, ana_id)
    _link(client, event_id, bruno_id)

    response = client.post(
        f"/events/{event_id}/settlements",
        json={
            "from_participant_id": bruno_id,
            "to_participant_id": ana_id,
            "amount": 25.0,
            "note": "Efectivo en el asado",
        },
    )
    assert response.status_code == 201
    settlement_id = response.json()["id"]
    assert isinstance(settlement_id, int)

    listed = client.get(f"/events/{event_id}/settlements").json()
    assert len(listed) == 1
    row = listed[0]
    assert row["id"] == settlement_id
    assert row["from_participant_id"] == bruno_id
    assert row["from_name"] == "Bruno"
    assert row["to_participant_id"] == ana_id
    assert row["to_name"] == "Ana"
    assert row["amount"] == 25.0
    assert row["note"] == "Efectivo en el asado"
    assert "created_at" in row


def test_create_settlement_without_note_defaults_to_null(api_client):
    client = api_client

    ana_id = _create_participant(client, "Ana")
    bruno_id = _create_participant(client, "Bruno")
    event_id = _create_event(client, "Cumple")
    _link(client, event_id, ana_id)
    _link(client, event_id, bruno_id)

    _settle(client, event_id, bruno_id, ana_id, 10.0)

    listed = client.get(f"/events/{event_id}/settlements").json()
    assert listed[0]["note"] is None


def test_get_event_settlements_on_event_with_none_returns_empty_list(api_client):
    client = api_client

    event_id = _create_event(client, "Vacio")
    response = client.get(f"/events/{event_id}/settlements")
    assert response.status_code == 200
    assert response.json() == []


# --- Validation failures ---------------------------------------------------------


def test_create_settlement_unknown_event_returns_404(api_client):
    client = api_client

    ana_id = _create_participant(client, "Ana")
    bruno_id = _create_participant(client, "Bruno")

    response = client.post(
        "/events/999999/settlements",
        json={"from_participant_id": ana_id, "to_participant_id": bruno_id, "amount": 10.0},
    )
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_create_settlement_participant_not_in_event_returns_422(api_client):
    client = api_client

    ana_id = _create_participant(client, "Ana")
    bruno_id = _create_participant(client, "Bruno")
    event_id = _create_event(client, "Cumple")
    _link(client, event_id, ana_id)
    # Bruno is deliberately NOT linked to this event.

    response = client.post(
        f"/events/{event_id}/settlements",
        json={"from_participant_id": bruno_id, "to_participant_id": ana_id, "amount": 10.0},
    )
    assert response.status_code == 422
    assert "not a participant of" in response.json()["detail"]


def test_create_settlement_from_equals_to_returns_422(api_client):
    client = api_client

    ana_id = _create_participant(client, "Ana")
    event_id = _create_event(client, "Cumple")
    _link(client, event_id, ana_id)

    response = client.post(
        f"/events/{event_id}/settlements",
        json={"from_participant_id": ana_id, "to_participant_id": ana_id, "amount": 10.0},
    )
    assert response.status_code == 422
    assert "cannot settle with themselves" in response.json()["detail"]


@pytest.mark.parametrize("amount", [0, -5.0])
def test_create_settlement_non_positive_amount_returns_422(api_client, amount):
    client = api_client

    ana_id = _create_participant(client, "Ana")
    bruno_id = _create_participant(client, "Bruno")
    event_id = _create_event(client, "Cumple")
    _link(client, event_id, ana_id)
    _link(client, event_id, bruno_id)

    # Rejected by Pydantic's Field(gt=0) before db.create_settlement ever
    # runs -- this is FastAPI-level 422, not the db-layer ValueError path.
    response = client.post(
        f"/events/{event_id}/settlements",
        json={"from_participant_id": bruno_id, "to_participant_id": ana_id, "amount": amount},
    )
    assert response.status_code == 422

    # No settlement was persisted.
    assert client.get(f"/events/{event_id}/settlements").json() == []


# --- Balance math end-to-end via the API ------------------------------------------


def test_settlement_reduces_net_balance_partial_then_full(api_client, image_upload_files):
    client = api_client

    ana_id = _create_participant(client, "Ana")
    bruno_id = _create_participant(client, "Bruno")
    event_id = _create_event(client, "Cena")
    _link(client, event_id, ana_id)
    _link(client, event_id, bruno_id)

    # Ana pays a $100 receipt; Bruno consumes $60 of it, Ana consumes $40.
    receipt_id = _upload_receipt(client, event_id, ana_id, 100.0, image_upload_files)
    item_id = _create_item(client, receipt_id, "Comida", 100.0)
    _assign(
        client,
        item_id,
        [
            {"participant_id": ana_id, "share": 0.4},
            {"participant_id": bruno_id, "share": 0.6},
        ],
    )

    balances = _event_balances_by_name(client, event_id)
    assert balances["Ana"]["total_paid"] == 100.0
    assert balances["Ana"]["total_consumed"] == pytest.approx(40.0)
    assert balances["Ana"]["net_balance"] == pytest.approx(60.0)
    assert balances["Bruno"]["total_consumed"] == pytest.approx(60.0)
    assert balances["Bruno"]["net_balance"] == pytest.approx(-60.0)

    overall_before = _overall_balances_by_name(client)
    assert overall_before["Ana"]["total_net_balance"] == pytest.approx(60.0)
    assert overall_before["Bruno"]["total_net_balance"] == pytest.approx(-60.0)

    # Bruno partially settles 40 of his 60 debt to Ana.
    _settle(client, event_id, bruno_id, ana_id, 40.0)

    balances = _event_balances_by_name(client, event_id)
    assert balances["Bruno"]["total_settled_sent"] == pytest.approx(40.0)
    assert balances["Bruno"]["total_settled_received"] == pytest.approx(0.0)
    assert balances["Bruno"]["net_balance"] == pytest.approx(-20.0)

    assert balances["Ana"]["total_settled_received"] == pytest.approx(40.0)
    assert balances["Ana"]["total_settled_sent"] == pytest.approx(0.0)
    # Ana's net decreased by exactly the settled amount (was +60, now +20).
    assert balances["Ana"]["net_balance"] == pytest.approx(20.0)

    overall = _overall_balances_by_name(client)
    assert overall["Ana"]["total_net_balance"] == pytest.approx(20.0)
    assert overall["Bruno"]["total_net_balance"] == pytest.approx(-20.0)
    net_sum = sum(row["total_net_balance"] for row in overall.values())
    assert net_sum == pytest.approx(0.0, abs=1e-9)

    # Bruno settles the remaining 20 -- his debt is now fully cleared.
    _settle(client, event_id, bruno_id, ana_id, 20.0)

    balances = _event_balances_by_name(client, event_id)
    assert balances["Bruno"]["total_settled_sent"] == pytest.approx(60.0)
    assert balances["Bruno"]["net_balance"] == pytest.approx(0.0)
    assert balances["Ana"]["net_balance"] == pytest.approx(0.0)

    overall = _overall_balances_by_name(client)
    assert overall["Bruno"]["total_net_balance"] == pytest.approx(0.0)
    assert overall["Ana"]["total_net_balance"] == pytest.approx(0.0)


def test_event_with_no_receipts_only_settlements(api_client):
    """A settlement between participants of an event with no receipts at
    all still moves the net balance -- paid/consumed both stay at 0. A cash
    transfer with no underlying debt makes the receiver *owe* the sender
    back (net_balance is "amount owed to this person": sending money raises
    it, receiving money lowers it), per the view's
    `+ total_settled_sent - total_settled_received` formula."""
    client = api_client

    ana_id = _create_participant(client, "Ana")
    bruno_id = _create_participant(client, "Bruno")
    event_id = _create_event(client, "Solo pagos")
    _link(client, event_id, ana_id)
    _link(client, event_id, bruno_id)

    _settle(client, event_id, bruno_id, ana_id, 15.0)

    balances = _event_balances_by_name(client, event_id)
    assert balances["Ana"]["total_paid"] == 0.0
    assert balances["Ana"]["total_consumed"] == 0.0
    assert balances["Ana"]["total_settled_received"] == pytest.approx(15.0)
    assert balances["Ana"]["net_balance"] == pytest.approx(-15.0)

    assert balances["Bruno"]["total_settled_sent"] == pytest.approx(15.0)
    assert balances["Bruno"]["net_balance"] == pytest.approx(15.0)


# --- DELETE /settlements/{id} -----------------------------------------------------


def test_delete_settlement_restores_previous_balances(api_client, image_upload_files):
    client = api_client

    ana_id = _create_participant(client, "Ana")
    bruno_id = _create_participant(client, "Bruno")
    event_id = _create_event(client, "Salida")
    _link(client, event_id, ana_id)
    _link(client, event_id, bruno_id)

    receipt_id = _upload_receipt(client, event_id, ana_id, 50.0, image_upload_files)
    item_id = _create_item(client, receipt_id, "Bebidas", 50.0)
    _assign(client, item_id, [{"participant_id": bruno_id, "share": 1.0}])

    balances_before = _event_balances_by_name(client, event_id)
    assert balances_before["Bruno"]["net_balance"] == pytest.approx(-50.0)
    assert balances_before["Ana"]["net_balance"] == pytest.approx(50.0)

    settlement_id = _settle(client, event_id, bruno_id, ana_id, 30.0)

    balances_after_settle = _event_balances_by_name(client, event_id)
    assert balances_after_settle["Bruno"]["net_balance"] == pytest.approx(-20.0)
    assert balances_after_settle["Ana"]["net_balance"] == pytest.approx(20.0)

    response = client.delete(f"/settlements/{settlement_id}")
    assert response.status_code == 204

    balances_after_delete = _event_balances_by_name(client, event_id)
    assert balances_after_delete["Bruno"]["net_balance"] == pytest.approx(-50.0)
    assert balances_after_delete["Ana"]["net_balance"] == pytest.approx(50.0)
    assert balances_after_delete["Bruno"]["total_settled_sent"] == 0.0
    assert balances_after_delete["Ana"]["total_settled_received"] == 0.0

    assert client.get(f"/events/{event_id}/settlements").json() == []


def test_delete_unknown_settlement_returns_404(api_client):
    client = api_client

    response = client.delete("/settlements/999999")
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


# --- GET /settlements (cross-event) -----------------------------------------------


def test_get_all_settlements_includes_event_id_and_name(api_client):
    client = api_client

    ana_id = _create_participant(client, "Ana")
    bruno_id = _create_participant(client, "Bruno")
    carla_id = _create_participant(client, "Carla")

    event1_id = _create_event(client, "Asado")
    _link(client, event1_id, ana_id)
    _link(client, event1_id, bruno_id)

    event2_id = _create_event(client, "Playa")
    _link(client, event2_id, ana_id)
    _link(client, event2_id, carla_id)

    _settle(client, event1_id, bruno_id, ana_id, 12.0)
    _settle(client, event2_id, carla_id, ana_id, 8.0)

    all_settlements = client.get("/settlements").json()
    assert len(all_settlements) == 2

    by_event_name = {row["event_name"]: row for row in all_settlements}
    assert by_event_name["Asado"]["event_id"] == event1_id
    assert by_event_name["Asado"]["from_name"] == "Bruno"
    assert by_event_name["Asado"]["to_name"] == "Ana"
    assert by_event_name["Asado"]["amount"] == 12.0

    assert by_event_name["Playa"]["event_id"] == event2_id
    assert by_event_name["Playa"]["from_name"] == "Carla"
    assert by_event_name["Playa"]["amount"] == 8.0


def test_get_all_settlements_empty_when_none_exist(api_client):
    client = api_client

    response = client.get("/settlements")
    assert response.status_code == 200
    assert response.json() == []


# --- Event deletion cleans up settlements ------------------------------------------


def test_delete_event_removes_its_settlements(api_client):
    """Deleting an event must also delete its settlements. Without this
    cleanup the orphaned rows are invisible to the whole API (the event's
    settlement listing 404s and GET /settlements inner-joins events) but
    still trip the delete_participant guard, permanently blocking the
    deletion of both participants."""
    client = api_client

    ana_id = _create_participant(client, "Ana")
    bruno_id = _create_participant(client, "Bruno")
    event_id = _create_event(client, "Efimero")
    _link(client, event_id, ana_id)
    _link(client, event_id, bruno_id)

    _settle(client, event_id, bruno_id, ana_id, 5.0)

    response = client.delete(f"/events/{event_id}")
    assert response.status_code == 204

    # No orphaned settlement remains anywhere.
    assert client.get("/settlements").json() == []

    # Both participants can be deleted again once the event is gone.
    assert client.delete(f"/participants/{bruno_id}").status_code == 204
    assert client.delete(f"/participants/{ana_id}").status_code == 204


# --- Participant deletion guard extended to settlements ---------------------------


def test_delete_participant_involved_in_settlement_returns_409_and_survives(api_client):
    client = api_client

    ana_id = _create_participant(client, "Ana")
    bruno_id = _create_participant(client, "Bruno")
    event_id = _create_event(client, "Cumple")
    _link(client, event_id, ana_id)
    _link(client, event_id, bruno_id)

    _settle(client, event_id, bruno_id, ana_id, 5.0)

    # Both the sender and the receiver of a settlement are protected.
    response_sender = client.delete(f"/participants/{bruno_id}")
    assert response_sender.status_code == 409

    response_receiver = client.delete(f"/participants/{ana_id}")
    assert response_receiver.status_code == 409

    remaining = {p["id"] for p in client.get("/participants").json()}
    assert {ana_id, bruno_id} <= remaining

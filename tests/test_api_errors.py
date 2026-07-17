"""API-level error-path tests: HTTP status codes and error shapes for the
invariants db.py enforces (services.value_error_to_http maps "does not
exist" messages to 404, everything else to 422). These deliberately do NOT
repeat db-layer unit tests already covered in test_db_*.py -- each test here
exists to prove the FastAPI wiring (status code, response shape) is correct,
not to re-validate the underlying business rule."""


def _create_participant(client, name: str) -> int:
    return client.post("/participants", json={"name": name}).json()["id"]


def _create_event(client, name: str) -> int:
    return client.post("/events", json={"name": name}).json()["id"]


def test_put_assignments_shares_not_summing_to_one_returns_422(api_client, image_upload_files):
    client = api_client
    ana_id = _create_participant(client, "Ana")
    bruno_id = _create_participant(client, "Bruno")
    event_id = _create_event(client, "Event")
    client.post(f"/events/{event_id}/participants", json={"participant_id": ana_id})
    client.post(f"/events/{event_id}/participants", json={"participant_id": bruno_id})

    receipt_id = client.post(
        f"/events/{event_id}/receipts",
        data={"payer_participant_id": ana_id, "total": 10.0},
        files=image_upload_files(),
    ).json()["id"]
    item_id = client.post(
        f"/receipts/{receipt_id}/items", json={"name": "Item", "price": 10.0}
    ).json()[0]["id"]

    response = client.put(
        f"/items/{item_id}/assignments",
        json=[
            {"participant_id": ana_id, "share": 0.5},
            {"participant_id": bruno_id, "share": 0.4},
        ],
    )

    assert response.status_code == 422
    assert "sum to 1.0" in response.json()["detail"]


def test_put_assignments_participant_not_in_event_returns_422(api_client, image_upload_files):
    client = api_client
    ana_id = _create_participant(client, "Ana")
    outsider_id = _create_participant(client, "Outsider")
    event_id = _create_event(client, "Event")
    client.post(f"/events/{event_id}/participants", json={"participant_id": ana_id})

    receipt_id = client.post(
        f"/events/{event_id}/receipts",
        data={"payer_participant_id": ana_id, "total": 10.0},
        files=image_upload_files(),
    ).json()["id"]
    item_id = client.post(
        f"/receipts/{receipt_id}/items", json={"name": "Item", "price": 10.0}
    ).json()[0]["id"]

    response = client.put(
        f"/items/{item_id}/assignments",
        json=[
            {"participant_id": ana_id, "share": 0.5},
            {"participant_id": outsider_id, "share": 0.5},
        ],
    )

    assert response.status_code == 422
    assert "not a participant of event" in response.json()["detail"]


def test_put_assignments_unknown_item_returns_404(api_client):
    client = api_client
    ana_id = _create_participant(client, "Ana")

    response = client.put(
        "/items/999999/assignments",
        json=[{"participant_id": ana_id, "share": 1.0}],
    )

    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_post_receipt_payer_not_in_event_returns_422(api_client, image_upload_files):
    client = api_client
    ana_id = _create_participant(client, "Ana")
    event_id = _create_event(client, "Event")
    # Ana is never linked to this event.

    response = client.post(
        f"/events/{event_id}/receipts",
        data={"payer_participant_id": ana_id, "total": 10.0},
        files=image_upload_files(),
    )

    assert response.status_code == 422
    assert "not a participant of" in response.json()["detail"]


def test_post_receipt_unknown_event_returns_404(api_client, image_upload_files):
    client = api_client
    ana_id = _create_participant(client, "Ana")

    response = client.post(
        "/events/999999/receipts",
        data={"payer_participant_id": ana_id, "total": 10.0},
        files=image_upload_files(),
    )

    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_get_event_receipts_unknown_event_returns_404(api_client):
    response = api_client.get("/events/999999/receipts")
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_get_event_unknown_event_returns_404(api_client):
    response = api_client.get("/events/999999")
    assert response.status_code == 404


def test_get_event_balances_unknown_event_returns_404(api_client):
    response = api_client.get("/events/999999/balances")
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_add_participant_to_unknown_event_returns_404(api_client):
    client = api_client
    ana_id = _create_participant(client, "Ana")
    response = client.post(
        "/events/999999/participants", json={"participant_id": ana_id}
    )
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]

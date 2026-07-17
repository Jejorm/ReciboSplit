"""API tests for GET /events/{event_id}/receipts: listing behavior beyond
what test_api_flow.py already exercises (single receipt, happy path). Covers
the "event with no receipts" and "one payer vs. multiple receipts per event"
cases called out in test-agent's responsibilities."""


def _create_participant(client, name: str) -> int:
    return client.post("/participants", json={"name": name}).json()["id"]


def _create_event(client, name: str) -> int:
    return client.post("/events", json={"name": name}).json()["id"]


def _link(client, event_id: int, participant_id: int) -> None:
    client.post(f"/events/{event_id}/participants", json={"participant_id": participant_id})


def _upload_receipt(client, event_id: int, payer_id: int, total: float, image_upload_files) -> dict:
    response = client.post(
        f"/events/{event_id}/receipts",
        data={"payer_participant_id": payer_id, "total": total},
        files=image_upload_files(),
    )
    assert response.status_code == 201
    return response.json()


def test_event_with_participants_but_no_receipts_returns_empty_list(api_client):
    client = api_client
    ana_id = _create_participant(client, "Ana")
    event_id = _create_event(client, "Empty event")
    _link(client, event_id, ana_id)

    response = client.get(f"/events/{event_id}/receipts")

    assert response.status_code == 200
    assert response.json() == []


def test_single_payer_with_multiple_receipts_in_one_event(api_client, image_upload_files):
    """One payer uploads two separate receipts for the same event -- both
    must be listed independently, not merged or overwritten."""
    client = api_client
    ana_id = _create_participant(client, "Ana")
    event_id = _create_event(client, "Weekend trip")
    _link(client, event_id, ana_id)

    _upload_receipt(client, event_id, ana_id, 30.0, image_upload_files)
    _upload_receipt(client, event_id, ana_id, 45.5, image_upload_files)

    receipts = client.get(f"/events/{event_id}/receipts").json()

    assert len(receipts) == 2
    totals = sorted(r["total_amount"] for r in receipts)
    assert totals == [30.0, 45.5]
    assert all(r["payer_name"] == "Ana" for r in receipts)


def test_multiple_receipts_with_different_payers_in_one_event(api_client, image_upload_files):
    client = api_client
    ana_id = _create_participant(client, "Ana")
    bruno_id = _create_participant(client, "Bruno")
    event_id = _create_event(client, "Weekend trip")
    _link(client, event_id, ana_id)
    _link(client, event_id, bruno_id)

    _upload_receipt(client, event_id, ana_id, 30.0, image_upload_files)
    _upload_receipt(client, event_id, bruno_id, 15.0, image_upload_files)

    receipts = client.get(f"/events/{event_id}/receipts").json()

    assert len(receipts) == 2
    payers_by_total = {r["total_amount"]: r["payer_name"] for r in receipts}
    assert payers_by_total == {30.0: "Ana", 15.0: "Bruno"}

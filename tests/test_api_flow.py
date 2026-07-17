"""Integration test: the full Phase 1 acceptance scenario driven entirely
through the HTTP API (main.py), matching PROJECT_STATUS.md's "Definition of
Done" table exactly. This is the one test that exercises every endpoint in
the write path end to end, using FastAPI's TestClient over a real (but
throwaway, local-only) SQLite database -- not a mock.

Also covers, opportunistically (no need for a separate test):
- POST /receipts/{id}/items accepting a LIST payload (event 1's items).
- POST /receipts/{id}/items accepting a SINGLE object payload (event 2's item).
- GET /events/{id}/receipts listing an uploaded receipt.
"""

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


def _assign(client, item_id: int, assignments: list[dict]) -> None:
    response = client.put(f"/items/{item_id}/assignments", json=assignments)
    assert response.status_code == 200


def test_full_acceptance_scenario_via_api(api_client, image_upload_files):
    client = api_client

    ana_id = _create_participant(client, "Ana")
    bruno_id = _create_participant(client, "Bruno")
    carla_id = _create_participant(client, "Carla")

    event1_id = _create_event(client, "Asado sabado")
    _link(client, event1_id, ana_id)
    _link(client, event1_id, bruno_id)
    _link(client, event1_id, carla_id)

    event2_id = _create_event(client, "Dia de playa")
    _link(client, event2_id, bruno_id)
    _link(client, event2_id, carla_id)

    receipt1_id = _upload_receipt(client, event1_id, ana_id, 90.0, image_upload_files)

    # POST /receipts/{id}/items with a LIST payload.
    items_response = client.post(
        f"/receipts/{receipt1_id}/items",
        json=[
            {"name": "Carne", "price": 60.0},
            {"name": "Bebidas", "price": 30.0},
        ],
    )
    assert items_response.status_code == 201
    created_items = items_response.json()
    assert len(created_items) == 2
    carne_id = next(i["id"] for i in created_items if i["description"] == "Carne")
    bebidas_id = next(i["id"] for i in created_items if i["description"] == "Bebidas")

    _assign(
        client,
        carne_id,
        [
            {"participant_id": ana_id, "share": 1 / 3},
            {"participant_id": bruno_id, "share": 1 / 3},
            {"participant_id": carla_id, "share": 1 / 3},
        ],
    )
    _assign(
        client,
        bebidas_id,
        [
            {"participant_id": bruno_id, "share": 0.5},
            {"participant_id": carla_id, "share": 0.5},
        ],
    )

    receipt2_id = _upload_receipt(client, event2_id, carla_id, 40.0, image_upload_files)

    # POST /receipts/{id}/items with a SINGLE object payload.
    single_item_response = client.post(
        f"/receipts/{receipt2_id}/items",
        json={"name": "Snacks", "price": 40.0},
    )
    assert single_item_response.status_code == 201
    snacks_created = single_item_response.json()
    assert len(snacks_created) == 1
    snacks_id = snacks_created[0]["id"]

    _assign(
        client,
        snacks_id,
        [
            {"participant_id": bruno_id, "share": 0.5},
            {"participant_id": carla_id, "share": 0.5},
        ],
    )

    # --- Assert exact balances via the API ------------------------------------

    event1_balances = {
        row["participant_name"]: row
        for row in client.get(f"/events/{event1_id}/balances").json()
    }
    assert event1_balances["Ana"]["total_paid"] == 90.0
    assert event1_balances["Ana"]["total_consumed"] == 20.0
    assert event1_balances["Ana"]["net_balance"] == 70.0
    assert event1_balances["Bruno"]["net_balance"] == -35.0
    assert event1_balances["Carla"]["net_balance"] == -35.0

    event2_balances = {
        row["participant_name"]: row
        for row in client.get(f"/events/{event2_id}/balances").json()
    }
    assert "Ana" not in event2_balances
    assert event2_balances["Bruno"]["net_balance"] == -20.0
    assert event2_balances["Carla"]["net_balance"] == 20.0

    overall = {
        row["participant_name"]: row for row in client.get("/balances").json()
    }
    assert overall["Ana"]["total_paid_all_events"] == 90.0
    assert overall["Ana"]["total_consumed_all_events"] == 20.0
    assert overall["Ana"]["total_net_balance"] == 70.0

    assert overall["Bruno"]["total_paid_all_events"] == 0.0
    assert overall["Bruno"]["total_consumed_all_events"] == 55.0
    assert overall["Bruno"]["total_net_balance"] == -55.0

    assert overall["Carla"]["total_paid_all_events"] == 40.0
    assert overall["Carla"]["total_consumed_all_events"] == 55.0
    assert overall["Carla"]["total_net_balance"] == -15.0

    net_sum = sum(row["total_net_balance"] for row in overall.values())
    assert abs(net_sum) < 1e-9

    # --- GET /events/{id}/receipts lists the uploaded receipt -----------------

    event1_receipts = client.get(f"/events/{event1_id}/receipts").json()
    assert len(event1_receipts) == 1
    assert event1_receipts[0]["payer_name"] == "Ana"
    assert event1_receipts[0]["total_amount"] == 90.0

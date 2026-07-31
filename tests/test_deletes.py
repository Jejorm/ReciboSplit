"""Integration tests for the three destructive DELETE endpoints added in
Phase 2 Task 7: DELETE /participants/{id}, DELETE /events/{id}, and
DELETE /data, plus the item rename/delete endpoints (PATCH /items/{id},
DELETE /items/{id}). Uses the same offline fixtures/TestClient pattern as
tests/test_api_flow.py (a fresh, throwaway, local-only SQLite db per test).

Covers:
- Deleting a participant with no financial history (204).
- Refusing to delete a participant who paid a receipt / has an assignment
  (409), and confirming nothing was partially deleted.
- Deleting an unknown participant id (404).
- Deleting an event cascades its receipts/items/assignments (204), and the
  event and its receipts become unreachable afterward (404).
- Deleting an unknown event id (404).
- DELETE /data wipes every table (200) and removes uploaded files, leaving
  GET /participants and GET /balances empty.
- Renaming an item (200) and confirming the new description round-trips
  through GET /receipts/{id}.
- Renaming an unknown item (404) and an empty-description rename (422,
  Pydantic-level, no DB call, original description untouched).
- Deleting an item (204) and confirming it disappears, including cascade
  cleanup of its item_assignments.
- Deleting an unknown item (404).
"""

from pathlib import Path


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


# --- DELETE /participants/{id} -----------------------------------------------


def test_delete_participant_with_no_history_returns_204_and_disappears(api_client):
    client = api_client

    participant_id = _create_participant(client, "Dana")

    response = client.delete(f"/participants/{participant_id}")
    assert response.status_code == 204

    remaining = client.get("/participants").json()
    assert all(p["id"] != participant_id for p in remaining)


def test_delete_participant_who_paid_a_receipt_returns_409_and_survives(
    api_client, image_upload_files
):
    client = api_client

    payer_id = _create_participant(client, "Ezequiel")
    event_id = _create_event(client, "Cumple")
    _link(client, event_id, payer_id)
    _upload_receipt(client, event_id, payer_id, 50.0, image_upload_files)

    response = client.delete(f"/participants/{payer_id}")
    assert response.status_code == 409

    remaining = client.get("/participants").json()
    assert any(p["id"] == payer_id for p in remaining)


def test_delete_participant_with_item_assignment_returns_409_and_survives(
    api_client, image_upload_files
):
    client = api_client

    payer_id = _create_participant(client, "Fede")
    consumer_id = _create_participant(client, "Gaby")
    event_id = _create_event(client, "Picnic")
    _link(client, event_id, payer_id)
    _link(client, event_id, consumer_id)

    receipt_id = _upload_receipt(client, event_id, payer_id, 20.0, image_upload_files)
    items_response = client.post(
        f"/receipts/{receipt_id}/items", json={"name": "Torta", "price": 20.0}
    )
    assert items_response.status_code == 201
    item_id = items_response.json()[0]["id"]
    _assign(client, item_id, [{"participant_id": consumer_id, "share": 1.0}])

    response = client.delete(f"/participants/{consumer_id}")
    assert response.status_code == 409

    remaining = client.get("/participants").json()
    assert any(p["id"] == consumer_id for p in remaining)


def test_delete_unknown_participant_returns_404(api_client):
    client = api_client

    response = client.delete("/participants/999999")
    assert response.status_code == 404


# --- DELETE /events/{id} -------------------------------------------------------


def test_delete_event_cascades_receipts_items_and_assignments(api_client, image_upload_files):
    client = api_client

    payer_id = _create_participant(client, "Hugo")
    consumer_id = _create_participant(client, "Ines")
    event_id = _create_event(client, "Asado")
    _link(client, event_id, payer_id)
    _link(client, event_id, consumer_id)

    receipt_id = _upload_receipt(client, event_id, payer_id, 30.0, image_upload_files)
    items_response = client.post(
        f"/receipts/{receipt_id}/items", json={"name": "Chorizo", "price": 30.0}
    )
    assert items_response.status_code == 201
    item_id = items_response.json()[0]["id"]
    _assign(client, item_id, [{"participant_id": consumer_id, "share": 1.0}])

    response = client.delete(f"/events/{event_id}")
    assert response.status_code == 204

    assert client.get(f"/events/{event_id}").status_code == 404
    assert client.get(f"/events/{event_id}/receipts").status_code == 404
    assert client.get(f"/receipts/{receipt_id}").status_code == 404
    assert client.get(f"/items/{item_id}/assignments").status_code == 404

    # The participants themselves are untouched -- only the event's data
    # (and their membership link) is cascade-deleted.
    remaining = {p["id"] for p in client.get("/participants").json()}
    assert {payer_id, consumer_id} <= remaining


def test_delete_unknown_event_returns_404(api_client):
    client = api_client

    response = client.delete("/events/999999")
    assert response.status_code == 404


# --- DELETE /data ---------------------------------------------------------------


def test_delete_all_data_wipes_everything(api_client, image_upload_files, tmp_path):
    client = api_client

    ana_id = _create_participant(client, "Ana")
    bruno_id = _create_participant(client, "Bruno")

    event_id = _create_event(client, "Salida")
    _link(client, event_id, ana_id)
    _link(client, event_id, bruno_id)

    receipt_id = _upload_receipt(client, event_id, ana_id, 10.0, image_upload_files)
    items_response = client.post(
        f"/receipts/{receipt_id}/items", json={"name": "Cafe", "price": 10.0}
    )
    assert items_response.status_code == 201
    item_id = items_response.json()[0]["id"]
    _assign(
        client,
        item_id,
        [
            {"participant_id": ana_id, "share": 0.5},
            {"participant_id": bruno_id, "share": 0.5},
        ],
    )

    uploads_dir = tmp_path / "uploads"
    assert uploads_dir.exists()
    assert any(uploads_dir.iterdir())

    response = client.delete("/data")
    assert response.status_code == 200
    assert response.json() == {"status": "all data deleted"}

    assert client.get("/participants").json() == []
    assert client.get("/balances").json() == []
    assert client.get("/events").json() == []

    # The uploads directory stays in place, but no files remain in it.
    assert uploads_dir.exists()
    assert list(uploads_dir.iterdir()) == []


# --- PATCH /items/{item_id} (rename) --------------------------------------------


def _create_item(client, receipt_id: int, name: str, price: float) -> int:
    response = client.post(
        f"/receipts/{receipt_id}/items", json={"name": name, "price": price}
    )
    assert response.status_code == 201
    return response.json()[0]["id"]


def test_rename_item_returns_200_and_persists(api_client, image_upload_files):
    client = api_client

    payer_id = _create_participant(client, "Julia")
    event_id = _create_event(client, "Cena")
    _link(client, event_id, payer_id)
    receipt_id = _upload_receipt(client, event_id, payer_id, 15.0, image_upload_files)
    item_id = _create_item(client, receipt_id, "Papas", 15.0)

    response = client.patch(f"/items/{item_id}", json={"description": "Papas fritas"})
    assert response.status_code == 200
    assert response.json() == {"id": item_id, "description": "Papas fritas"}

    # Don't just trust the PATCH response -- verify the rename round-trips
    # through the DB via a fresh GET.
    receipt = client.get(f"/receipts/{receipt_id}").json()
    renamed = next(item for item in receipt["items"] if item["id"] == item_id)
    assert renamed["description"] == "Papas fritas"


def test_rename_unknown_item_returns_404(api_client):
    client = api_client

    response = client.patch("/items/999999", json={"description": "Nada"})
    assert response.status_code == 404


def test_rename_item_with_empty_description_returns_422_and_leaves_item_untouched(
    api_client, image_upload_files
):
    client = api_client

    payer_id = _create_participant(client, "Karina")
    event_id = _create_event(client, "Reunion")
    _link(client, event_id, payer_id)
    receipt_id = _upload_receipt(client, event_id, payer_id, 8.0, image_upload_files)
    item_id = _create_item(client, receipt_id, "Pan", 8.0)

    response = client.patch(f"/items/{item_id}", json={"description": ""})
    assert response.status_code == 422

    # Pydantic validation rejects the empty string before any DB call, so
    # the original description must still be intact.
    receipt = client.get(f"/receipts/{receipt_id}").json()
    untouched = next(item for item in receipt["items"] if item["id"] == item_id)
    assert untouched["description"] == "Pan"


# --- DELETE /items/{item_id} -----------------------------------------------------


def test_delete_item_with_no_assignments_returns_204_and_disappears(
    api_client, image_upload_files
):
    client = api_client

    payer_id = _create_participant(client, "Leandro")
    event_id = _create_event(client, "Fiesta")
    _link(client, event_id, payer_id)
    receipt_id = _upload_receipt(client, event_id, payer_id, 12.0, image_upload_files)
    item_id = _create_item(client, receipt_id, "Helado", 12.0)

    response = client.delete(f"/items/{item_id}")
    assert response.status_code == 204

    assert client.get(f"/items/{item_id}/assignments").status_code == 404
    receipt = client.get(f"/receipts/{receipt_id}").json()
    assert all(item["id"] != item_id for item in receipt["items"])


def test_delete_unknown_item_returns_404(api_client):
    client = api_client

    response = client.delete("/items/999999")
    assert response.status_code == 404


def test_delete_item_with_assignments_cascades_item_assignments(
    api_client, image_upload_files
):
    client = api_client

    payer_id = _create_participant(client, "Mora")
    consumer_id = _create_participant(client, "Nico")
    event_id = _create_event(client, "Almuerzo")
    _link(client, event_id, payer_id)
    _link(client, event_id, consumer_id)
    receipt_id = _upload_receipt(client, event_id, payer_id, 18.0, image_upload_files)
    item_id = _create_item(client, receipt_id, "Ensalada", 18.0)
    _assign(client, item_id, [{"participant_id": consumer_id, "share": 1.0}])

    response = client.delete(f"/items/{item_id}")
    assert response.status_code == 204

    # The item's assignments are gone along with it, not left orphaned.
    assert client.get(f"/items/{item_id}/assignments").status_code == 404
    receipt = client.get(f"/receipts/{receipt_id}").json()
    assert all(item["id"] != item_id for item in receipt["items"])

    # The consumer participant itself is untouched -- only the item's own
    # assignment row is cascade-deleted.
    remaining = {p["id"] for p in client.get("/participants").json()}
    assert consumer_id in remaining

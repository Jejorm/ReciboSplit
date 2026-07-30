"""API-level tests for the per-event currency feature (display-only, no
conversion -- see schema.sql / db.py's update_event_currency). These
deliberately do NOT re-validate db.py's own invariants (already covered in
test_db_event_currency.py) -- each test here exists to prove the FastAPI
wiring (request/response shape, status codes) is correct."""


def _create_participant(client, name: str) -> int:
    return client.post("/participants", json={"name": name}).json()["id"]


def test_create_event_default_currency_is_usd(api_client):
    client = api_client
    event_id = client.post("/events", json={"name": "Asado"}).json()["id"]

    response = client.get(f"/events/{event_id}")

    assert response.status_code == 200
    assert response.json()["currency"] == "USD"


def test_create_event_explicit_currency_reflected_in_get(api_client):
    client = api_client
    event_id = client.post(
        "/events", json={"name": "Viaje a Brasil", "currency": "BRL"}
    ).json()["id"]

    response = client.get(f"/events/{event_id}")

    assert response.status_code == 200
    assert response.json()["currency"] == "BRL"


def test_list_events_includes_currency(api_client):
    client = api_client
    client.post("/events", json={"name": "Asado", "currency": "ARS"})

    response = client.get("/events")

    assert response.status_code == 200
    assert response.json()[0]["currency"] == "ARS"


def test_update_event_currency_happy_path(api_client):
    client = api_client
    event_id = client.post("/events", json={"name": "Asado"}).json()["id"]

    response = client.put(f"/events/{event_id}/currency", json={"currency": "EUR"})
    assert response.status_code == 204

    event = client.get(f"/events/{event_id}").json()
    assert event["currency"] == "EUR"


def test_update_event_currency_unknown_event_returns_404(api_client):
    client = api_client
    response = client.put("/events/999999/currency", json={"currency": "EUR"})

    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_extract_endpoint_response_includes_currency(
    api_client, image_upload_files, monkeypatch
):
    import main as main_module
    from vision import ExtractedItem, ExtractionResult

    client = api_client
    ana_id = _create_participant(client, "Ana")
    event_id = client.post("/events", json={"name": "Event"}).json()["id"]
    client.post(f"/events/{event_id}/participants", json={"participant_id": ana_id})
    receipt_id = client.post(
        f"/events/{event_id}/receipts",
        data={"payer_participant_id": ana_id, "total": 10.0},
        files=image_upload_files(),
    ).json()["id"]

    fake_result = ExtractionResult(
        items=[ExtractedItem(description="Coffee", price=10.0, quantity=1)],
        receipt_total=10.0,
        currency="EUR",
    )
    monkeypatch.setattr(
        main_module.vision, "extract_receipt_items", lambda image_path: fake_result
    )

    response = client.post(f"/receipts/{receipt_id}/extract")

    assert response.status_code == 200
    assert response.json()["currency"] == "EUR"


def test_extract_endpoint_currency_defaults_to_none(
    api_client, image_upload_files, monkeypatch
):
    import main as main_module
    from vision import ExtractedItem, ExtractionResult

    client = api_client
    ana_id = _create_participant(client, "Ana")
    event_id = client.post("/events", json={"name": "Event"}).json()["id"]
    client.post(f"/events/{event_id}/participants", json={"participant_id": ana_id})
    receipt_id = client.post(
        f"/events/{event_id}/receipts",
        data={"payer_participant_id": ana_id, "total": 10.0},
        files=image_upload_files(),
    ).json()["id"]

    fake_result = ExtractionResult(
        items=[ExtractedItem(description="Coffee", price=10.0, quantity=1)],
        receipt_total=10.0,
    )
    monkeypatch.setattr(
        main_module.vision, "extract_receipt_items", lambda image_path: fake_result
    )

    response = client.post(f"/receipts/{receipt_id}/extract")

    assert response.status_code == 200
    assert response.json()["currency"] is None

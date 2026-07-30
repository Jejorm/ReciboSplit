"""Tests for the Phase 2 vision extraction module (vision.py) and the
`POST /receipts/{receipt_id}/extract` endpoint.

HARD RULE: no test in this file may ever call the real OpenAI API or
require a valid OPENAI_API_KEY. Every path that would reach the network
is mocked at the Python level (`vision._call_openai`, `vision.OpenAI`
itself, or — for the endpoint tests — `vision.extract_receipt_items` as
seen by `main`). An autouse fixture also strips OPENAI_API_KEY from the
environment so any accidentally un-mocked call fails fast on auth
instead of silently reaching the network.

These tests deliberately do NOT re-check things already covered by
test_api_receipts.py / test_api_errors.py (e.g. generic 404 shape for
other endpoints) -- they focus on the extraction-specific contract:
the parser/validator, the total-mismatch warnings, the MIME guard, the
two `_call_openai` exception branches, and the endpoint's persistence
guarantees.
"""

import httpx
import openai
import pytest

import vision
from vision import (
    ExtractedItem,
    ExtractionError,
    ExtractionResult,
    _apply_tax_proration,
    _apply_total_warnings,
    _guess_mime_type,
    _parse_and_validate,
    extract_receipt_items,
)


@pytest.fixture(autouse=True)
def no_openai_api_key(monkeypatch):
    """Safety net: strip OPENAI_API_KEY so any accidentally un-mocked call
    to the OpenAI SDK fails immediately (auth error) rather than reaching
    the real network."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


# --- _parse_and_validate: valid payloads -------------------------------------


def test_parse_and_validate_valid_payload_multiple_items():
    raw_json = (
        '{"items": ['
        '{"description": "Milk", "price": 3.5, "quantity": 2}, '
        '{"description": "Bread", "price": 2.0, "quantity": 1}'
        '], "receipt_total": 6.0}'
    )

    result = _parse_and_validate(raw_json)

    assert isinstance(result, ExtractionResult)
    assert len(result.items) == 2
    assert result.items[0].description == "Milk"
    assert result.items[0].price == 3.5
    assert result.items[0].quantity == 2
    assert result.items[1].quantity == 1
    assert result.receipt_total == 6.0
    assert result.warnings == []


def test_parse_and_validate_quantity_defaults_to_one_when_omitted():
    raw_json = '{"items": [{"description": "Egg", "price": 1.0}], "receipt_total": 1.0}'

    result = _parse_and_validate(raw_json)

    assert result.items[0].quantity == 1


def test_parse_and_validate_tax_amount_defaults_to_zero_when_omitted():
    """Existing/legacy mocked payloads (and real receipts with no tax line)
    never send `tax_amount` -- the Pydantic default must cover them for
    free, with no per-fixture changes needed."""
    raw_json = (
        '{"items": [{"description": "Milk", "price": 3.5, "quantity": 2}], '
        '"receipt_total": 3.5}'
    )

    result = _parse_and_validate(raw_json)

    assert result.tax_amount == 0.0


def test_parse_and_validate_tax_amount_parsed_from_payload():
    raw_json = (
        '{"items": [{"description": "Milk", "price": 3.5, "quantity": 1}], '
        '"receipt_total": 3.85, "tax_amount": 0.35}'
    )

    result = _parse_and_validate(raw_json)

    assert result.tax_amount == 0.35


def test_parse_and_validate_tax_amount_negative_raises():
    raw_json = (
        '{"items": [{"description": "Milk", "price": 3.5, "quantity": 1}], '
        '"receipt_total": 3.5, "tax_amount": -0.01}'
    )

    with pytest.raises(ExtractionError):
        _parse_and_validate(raw_json)


def test_parse_and_validate_currency_parsed_from_payload():
    raw_json = (
        '{"items": [{"description": "Milk", "price": 3.5, "quantity": 1}], '
        '"receipt_total": 3.5, "currency": "EUR"}'
    )

    result = _parse_and_validate(raw_json)

    assert result.currency == "EUR"


def test_parse_and_validate_currency_defaults_to_none_when_omitted():
    """Existing/legacy mocked payloads (and real receipts where the model
    couldn't tell) never send `currency` -- the Pydantic default must
    cover them for free, with no per-fixture changes needed."""
    raw_json = (
        '{"items": [{"description": "Milk", "price": 3.5, "quantity": 1}], '
        '"receipt_total": 3.5}'
    )

    result = _parse_and_validate(raw_json)

    assert result.currency is None


def test_parse_and_validate_currency_explicit_null_gives_none():
    raw_json = (
        '{"items": [{"description": "Milk", "price": 3.5, "quantity": 1}], '
        '"receipt_total": 3.5, "currency": null}'
    )

    result = _parse_and_validate(raw_json)

    assert result.currency is None


# --- _parse_and_validate: malformed / invalid payloads -----------------------


def test_parse_and_validate_non_json_text_raises():
    with pytest.raises(ExtractionError):
        _parse_and_validate("this is not json at all")


def test_parse_and_validate_missing_items_key_raises():
    with pytest.raises(ExtractionError):
        _parse_and_validate('{"receipt_total": 5.0}')


def test_parse_and_validate_missing_receipt_total_raises():
    with pytest.raises(ExtractionError):
        _parse_and_validate('{"items": [{"description": "X", "price": 1.0}]}')


def test_parse_and_validate_empty_items_list_raises():
    with pytest.raises(ExtractionError):
        _parse_and_validate('{"items": [], "receipt_total": 5.0}')


def test_parse_and_validate_json_array_instead_of_object_raises():
    """A JSON array top-level payload hits the TypeError path: `**payload`
    on a list is not a valid kwargs expansion."""
    with pytest.raises(ExtractionError):
        _parse_and_validate("[1, 2, 3]")


def test_parse_and_validate_item_missing_description_raises():
    with pytest.raises(ExtractionError):
        _parse_and_validate('{"items": [{"price": 1.0}], "receipt_total": 1.0}')


def test_parse_and_validate_item_missing_price_raises():
    with pytest.raises(ExtractionError):
        _parse_and_validate('{"items": [{"description": "X"}], "receipt_total": 1.0}')


def test_parse_and_validate_item_empty_description_raises():
    with pytest.raises(ExtractionError):
        _parse_and_validate(
            '{"items": [{"description": "", "price": 1.0}], "receipt_total": 1.0}'
        )


def test_parse_and_validate_item_price_zero_raises():
    with pytest.raises(ExtractionError):
        _parse_and_validate(
            '{"items": [{"description": "X", "price": 0}], "receipt_total": 1.0}'
        )


def test_parse_and_validate_item_price_negative_raises():
    with pytest.raises(ExtractionError):
        _parse_and_validate(
            '{"items": [{"description": "X", "price": -1.0}], "receipt_total": 1.0}'
        )


def test_parse_and_validate_item_price_infinity_raises():
    """json.loads accepts the bare `Infinity` literal by default -- the
    Pydantic contract's allow_inf_nan=False must reject it anyway."""
    with pytest.raises(ExtractionError):
        _parse_and_validate(
            '{"items": [{"description": "X", "price": Infinity}], "receipt_total": 1.0}'
        )


def test_parse_and_validate_item_quantity_zero_raises():
    with pytest.raises(ExtractionError):
        _parse_and_validate(
            '{"items": [{"description": "X", "price": 1.0, "quantity": 0}], '
            '"receipt_total": 1.0}'
        )


# --- _apply_tax_proration -----------------------------------------------------


def _multi_result(
    prices: list[float], receipt_total: float, tax_amount: float = 0.0
) -> ExtractionResult:
    return ExtractionResult(
        items=[
            ExtractedItem(description=f"Item{i}", price=p, quantity=1)
            for i, p in enumerate(prices)
        ],
        receipt_total=receipt_total,
        tax_amount=tax_amount,
    )


def test_apply_tax_proration_no_tax_is_a_no_op():
    """tax_amount == 0.0 (the untaxed-receipt majority case): item prices
    must be left byte-for-byte as extracted."""
    result = _multi_result([80.0, 55.0], receipt_total=135.0, tax_amount=0.0)

    _apply_tax_proration(result)

    assert [item.price for item in result.items] == [80.0, 55.0]


def test_apply_tax_proration_real_bug_report_numbers():
    """The exact numbers from the tax-proration bug report: two items
    (80.0, 55.0) summing to 135.0 pre-tax, with a 13.50 (10% IVA) tax
    line. First item scales by the full factor (1 + 13.5/135 = 1.1) to
    88.0; the last item absorbs the rounding remainder to land the total
    on exactly 148.5 (135.0 + 13.5), not just approximately."""
    result = _multi_result([80.0, 55.0], receipt_total=148.5, tax_amount=13.5)

    _apply_tax_proration(result)

    assert [item.price for item in result.items] == [88.0, 60.5]
    assert sum(item.price for item in result.items) == pytest.approx(148.5)


def test_apply_tax_proration_tax_amount_field_stays_unprorated():
    """`ExtractionResult.tax_amount` is the original detected amount for
    UI display and must survive proration unchanged, even though the item
    prices it was folded into are mutated in place."""
    result = _multi_result([80.0, 55.0], receipt_total=148.5, tax_amount=13.5)

    _apply_tax_proration(result)

    assert result.tax_amount == 13.5


def test_apply_tax_proration_last_item_absorbs_rounding_remainder():
    """Naive independent per-item rounding would NOT sum exactly to the
    target total here: 33.34 * (1 + 0.01/100.0) rounds to 33.34, which
    (with the other two unchanged items at 33.33 each) sums to 100.00 --
    a cent short of the true target of 100.01. The last-item-absorbs-the-
    remainder trick must still land on the exact target instead."""
    result = _multi_result(
        [33.33, 33.33, 33.34], receipt_total=100.01, tax_amount=0.01
    )

    _apply_tax_proration(result)

    assert result.items[0].price == 33.33
    assert result.items[1].price == 33.33
    assert result.items[2].price == 33.35
    assert sum(item.price for item in result.items) == pytest.approx(100.01)


# --- _apply_total_warnings ----------------------------------------------------


def _result(price: float, receipt_total: float) -> ExtractionResult:
    return ExtractionResult(
        items=[ExtractedItem(description="X", price=price, quantity=1)],
        receipt_total=receipt_total,
    )


def test_apply_total_warnings_sum_matches_total_no_warning():
    result = _result(price=100.0, receipt_total=100.0)
    _apply_total_warnings(result)
    assert result.warnings == []


def test_apply_total_warnings_sum_more_than_total_warns():
    result = _result(price=100.02, receipt_total=100.0)
    _apply_total_warnings(result)
    assert len(result.warnings) == 1
    assert "more than" in result.warnings[0]


def test_apply_total_warnings_sum_much_less_than_total_warns():
    result = _result(price=69.99, receipt_total=100.0)
    _apply_total_warnings(result)
    assert len(result.warnings) == 1
    assert "much less" in result.warnings[0]


def test_apply_total_warnings_items_sum_in_old_70_to_90_band_now_warns():
    """Behavior change from this fix: before, the "too low" threshold was
    0.7 * receipt_total specifically to tolerate the always-missing tax
    portion. Since tax is now prorated into item prices before this check
    runs, that tolerance is gone -- an items_sum of 80% of receipt_total
    (which passed silently under the old 70% threshold) must now warn."""
    result = _result(price=80.0, receipt_total=100.0)
    _apply_total_warnings(result)
    assert len(result.warnings) == 1
    assert "much less" in result.warnings[0]


def test_apply_total_warnings_just_inside_upper_tolerance_no_warning():
    """items_sum == receipt_total + tolerance is NOT strictly greater, so
    no warning fires at the exact boundary."""
    result = _result(price=100.01, receipt_total=100.0)
    _apply_total_warnings(result)
    assert result.warnings == []


def test_apply_total_warnings_just_inside_lower_threshold_no_warning():
    """items_sum == 0.9 * receipt_total is NOT strictly less, so no
    warning fires at the exact boundary. (Threshold tightened from 0.7 to
    0.9 by the tax-proration fix -- see the 70-90% band test above for the
    behavior change this caused.)"""
    result = _result(price=90.0, receipt_total=100.0)
    _apply_total_warnings(result)
    assert result.warnings == []


# --- _guess_mime_type ----------------------------------------------------------


@pytest.mark.parametrize(
    "filename, expected_mime",
    [
        ("receipt.jpg", "image/jpeg"),
        ("receipt.jpeg", "image/jpeg"),
        ("receipt.png", "image/png"),
        ("receipt.webp", "image/webp"),
    ],
)
def test_guess_mime_type_supported_extensions(filename, expected_mime):
    assert _guess_mime_type(filename) == expected_mime


@pytest.mark.parametrize("filename", ["receipt.heic", "receipt.pdf"])
def test_guess_mime_type_rejects_unsupported_known_extensions(filename):
    with pytest.raises(ExtractionError):
        _guess_mime_type(filename)


@pytest.mark.parametrize("filename", ["receipt", "receipt.xyz123"])
def test_guess_mime_type_defaults_to_jpeg_for_unknown_extension(filename):
    assert _guess_mime_type(filename) == "image/jpeg"


# --- extract_receipt_items: pre-API-call short circuits -----------------------


def test_extract_receipt_items_nonexistent_path_raises_without_calling_api(
    tmp_path, monkeypatch
):
    call_mock_calls = []
    monkeypatch.setattr(
        vision, "_call_openai", lambda path: call_mock_calls.append(path) or "{}"
    )

    missing_path = str(tmp_path / "does-not-exist.jpg")

    with pytest.raises(ExtractionError):
        extract_receipt_items(missing_path)

    assert call_mock_calls == []


def test_extract_receipt_items_directory_path_raises_without_calling_api(
    tmp_path, monkeypatch
):
    call_mock_calls = []
    monkeypatch.setattr(
        vision, "_call_openai", lambda path: call_mock_calls.append(path) or "{}"
    )

    with pytest.raises(ExtractionError):
        extract_receipt_items(str(tmp_path))

    assert call_mock_calls == []


# --- extract_receipt_items: happy path with _call_openai mocked ---------------


def test_extract_receipt_items_happy_path(tmp_path, monkeypatch):
    image_path = tmp_path / "receipt.jpg"
    image_path.write_bytes(b"fake-jpeg-bytes")

    raw_json = (
        '{"items": [{"description": "Coffee", "price": 3.0, "quantity": 1}], '
        '"receipt_total": 10.0}'
    )
    monkeypatch.setattr(vision, "_call_openai", lambda path: raw_json)

    result = extract_receipt_items(str(image_path))

    assert isinstance(result, ExtractionResult)
    assert result.items[0].description == "Coffee"
    assert result.receipt_total == 10.0
    # sum (3.0) < 0.9 * 10.0 (9.0) -> total-mismatch warning must be applied.
    assert len(result.warnings) == 1
    assert "much less" in result.warnings[0]
    assert result.tax_amount == 0.0


def test_extract_receipt_items_prorates_tax_and_avoids_false_warning(
    tmp_path, monkeypatch
):
    """Full pipeline (parse -> proration -> warnings) with the real numbers
    from the tax-proration bug report: item prices get tax folded in
    before the total-mismatch check runs, so a tax-inclusive receipt_total
    that exactly matches the prorated sum must NOT warn."""
    image_path = tmp_path / "receipt.jpg"
    image_path.write_bytes(b"fake-jpeg-bytes")

    raw_json = (
        '{"items": ['
        '{"description": "Widget", "price": 80.0, "quantity": 1}, '
        '{"description": "Gadget", "price": 55.0, "quantity": 1}'
        '], "receipt_total": 148.5, "tax_amount": 13.5}'
    )
    monkeypatch.setattr(vision, "_call_openai", lambda path: raw_json)

    result = extract_receipt_items(str(image_path))

    assert [item.price for item in result.items] == [88.0, 60.5]
    assert result.tax_amount == 13.5
    assert result.warnings == []


# --- _call_openai exception branches (mock the OpenAI client class) -----------


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, *, return_value=None, side_effect=None):
        self._return_value = return_value
        self._side_effect = side_effect

    def create(self, **kwargs):
        if self._side_effect is not None:
            raise self._side_effect
        return self._return_value


class _FakeChat:
    def __init__(self, completions):
        self.completions = completions


class _FakeOpenAIClient:
    def __init__(self, completions):
        self.chat = _FakeChat(completions)


def _patch_openai_class(monkeypatch, *, return_value=None, side_effect=None):
    """Replace vision.OpenAI (the class used to build the client) with a
    fake constructor, so `_call_openai` never touches the network no
    matter what arguments it passes."""
    completions = _FakeCompletions(return_value=return_value, side_effect=side_effect)
    client = _FakeOpenAIClient(completions)

    def _fake_constructor(*args, **kwargs):
        return client

    monkeypatch.setattr(vision, "OpenAI", _fake_constructor)


@pytest.fixture
def real_image_path(tmp_path):
    """A tiny local file with a .jpg name -- its content is never sent
    anywhere because the OpenAI client itself is mocked out."""
    path = tmp_path / "receipt.jpg"
    path.write_bytes(b"fake-jpeg-bytes")
    return str(path)


def test_call_openai_api_timeout_error_has_distinct_message(monkeypatch, real_image_path):
    timeout_error = openai.APITimeoutError(request=httpx.Request("POST", "http://test"))
    _patch_openai_class(monkeypatch, side_effect=timeout_error)

    with pytest.raises(ExtractionError) as exc_info:
        vision._call_openai(real_image_path)

    assert "took too long" in str(exc_info.value)


def test_call_openai_generic_exception_has_unavailable_message(monkeypatch, real_image_path):
    _patch_openai_class(monkeypatch, side_effect=RuntimeError("boom"))

    with pytest.raises(ExtractionError) as exc_info:
        vision._call_openai(real_image_path)

    assert "unavailable" in str(exc_info.value)


@pytest.mark.parametrize("empty_content", [None, ""])
def test_call_openai_empty_response_raises(monkeypatch, real_image_path, empty_content):
    _patch_openai_class(
        monkeypatch, return_value=_FakeResponse(content=empty_content)
    )

    with pytest.raises(ExtractionError) as exc_info:
        vision._call_openai(real_image_path)

    assert "empty response" in str(exc_info.value)


def test_call_openai_returns_content_on_success(monkeypatch, real_image_path):
    _patch_openai_class(monkeypatch, return_value=_FakeResponse(content='{"ok": true}'))

    content = vision._call_openai(real_image_path)

    assert content == '{"ok": true}'


# --- POST /receipts/{receipt_id}/extract: endpoint tests ----------------------


def _create_participant(client, name: str) -> int:
    return client.post("/participants", json={"name": name}).json()["id"]


def _create_event(client, name: str) -> int:
    return client.post("/events", json={"name": name}).json()["id"]


def test_extract_endpoint_unknown_receipt_returns_404(api_client):
    response = api_client.post("/receipts/999999/extract")

    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]


def test_extract_endpoint_empty_image_path_returns_422(api_client, local_db):
    client = api_client
    ana_id = _create_participant(client, "Ana")
    event_id = _create_event(client, "Event")
    client.post(f"/events/{event_id}/participants", json={"participant_id": ana_id})

    # Bypass the upload endpoint (which always stores a real file) to
    # reach the "" sentinel the endpoint guards against.
    receipt_id = local_db.create_receipt(event_id, ana_id, 10.0, "")

    response = client.post(f"/receipts/{receipt_id}/extract")

    assert response.status_code == 422
    assert "manual item capture" in response.json()["detail"]


def test_extract_endpoint_extraction_error_returns_502_with_message(
    api_client, image_upload_files, monkeypatch
):
    import main as main_module

    client = api_client
    ana_id = _create_participant(client, "Ana")
    event_id = _create_event(client, "Event")
    client.post(f"/events/{event_id}/participants", json={"participant_id": ana_id})
    receipt_id = client.post(
        f"/events/{event_id}/receipts",
        data={"payer_participant_id": ana_id, "total": 10.0},
        files=image_upload_files(),
    ).json()["id"]

    def _raise_extraction_error(image_path):
        raise vision.ExtractionError("The vision service is unavailable right now.")

    monkeypatch.setattr(main_module.vision, "extract_receipt_items", _raise_extraction_error)

    response = client.post(f"/receipts/{receipt_id}/extract")

    assert response.status_code == 502
    assert response.json()["detail"] == "The vision service is unavailable right now."


def test_extract_endpoint_happy_path_does_not_persist_items(
    api_client, image_upload_files, monkeypatch
):
    import main as main_module

    client = api_client
    ana_id = _create_participant(client, "Ana")
    event_id = _create_event(client, "Event")
    client.post(f"/events/{event_id}/participants", json={"participant_id": ana_id})
    receipt_id = client.post(
        f"/events/{event_id}/receipts",
        data={"payer_participant_id": ana_id, "total": 10.0},
        files=image_upload_files(),
    ).json()["id"]

    fake_result = ExtractionResult(
        items=[
            ExtractedItem(description="Coffee", price=3.0, quantity=1),
            ExtractedItem(description="Bagel", price=2.5, quantity=2),
        ],
        receipt_total=10.0,
        warnings=["Item prices sum to much less than the receipt total"],
    )

    monkeypatch.setattr(
        main_module.vision, "extract_receipt_items", lambda image_path: fake_result
    )

    response = client.post(f"/receipts/{receipt_id}/extract")

    assert response.status_code == 200
    body = response.json()
    assert body["receipt_id"] == receipt_id
    assert body["receipt_total"] == 10.0
    assert len(body["items"]) == 2
    assert body["items"][0] == {"description": "Coffee", "price": 3.0, "quantity": 1}
    assert body["items"][1] == {"description": "Bagel", "price": 2.5, "quantity": 2}
    assert body["warnings"] == fake_result.warnings
    # tax_amount defaults to 0.0 when vision.extract_receipt_items detected
    # no tax line -- must still be present and correct in the response.
    assert body["tax_amount"] == 0.0

    # Non-persistence: the receipt must still show zero items after the
    # extraction proposal call.
    receipt_after = client.get(f"/receipts/{receipt_id}").json()
    assert receipt_after["items"] == []


def test_extract_endpoint_passes_through_prorated_items_and_tax_amount(
    api_client, image_upload_files, monkeypatch
):
    """The endpoint must surface the already-prorated item prices (tax
    folded in by vision.py) as well as the original, unprorated
    tax_amount, unchanged -- it does no proration math of its own."""
    import main as main_module

    client = api_client
    ana_id = _create_participant(client, "Ana")
    event_id = _create_event(client, "Event")
    client.post(f"/events/{event_id}/participants", json={"participant_id": ana_id})
    receipt_id = client.post(
        f"/events/{event_id}/receipts",
        data={"payer_participant_id": ana_id, "total": 148.5},
        files=image_upload_files(),
    ).json()["id"]

    fake_result = ExtractionResult(
        items=[
            ExtractedItem(description="Widget", price=88.0, quantity=1),
            ExtractedItem(description="Gadget", price=60.5, quantity=1),
        ],
        receipt_total=148.5,
        tax_amount=13.5,
        warnings=[],
    )

    monkeypatch.setattr(
        main_module.vision, "extract_receipt_items", lambda image_path: fake_result
    )

    response = client.post(f"/receipts/{receipt_id}/extract")

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0] == {"description": "Widget", "price": 88.0, "quantity": 1}
    assert body["items"][1] == {"description": "Gadget", "price": 60.5, "quantity": 1}
    assert body["tax_amount"] == 13.5
    assert body["warnings"] == []

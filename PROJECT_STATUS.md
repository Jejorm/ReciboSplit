# PROJECT_STATUS.md

Current status of ReciboSplit. Update this at the end of every work session.

## PROJECT COMPLETE — Phase 1 + Phase 2 both done

Phase 1 (manual capture, full day-by-day log preserved further down) and Phase 2 (automatic receipt recognition via OpenAI vision, strictly additive to Phase 1) are both functionally complete. Every Definition-of-Done item in both checklists is verified, including the two human-only checks:

- **Live MCP chat test** (asking the `recibosplit` server a balance question from inside Claude Code) — confirmed done by the user on 2026-07-29.
- **EN/ES language-switcher click-through** (Phase 2 Task 7) — confirmed done by the user on 2026-07-29.

Any new work from here starts a new phase/feature on top of a finished app.

### Post-completion fixes

- **2026-07-30 — Rename and delete individual items.** New `PATCH /items/{id}` (rename, `description` only) and `DELETE /items/{id}` (cascades its `item_assignments`) endpoints in `main.py`/`db.py`. `ItemList.jsx` got inline rename (edit/save/cancel) and a delete button next to the existing assign flow, wired through `frontend/src/api.js` with new EN/ES strings. 6 new cases in `tests/test_deletes.py` (rename 200/404/422, delete 204/404/cascade); full suite 121 passed. Verified live in the browser against the real "Asado Familiar" event/receipt #30: renamed "Iva" → "IVA (impuesto)" and confirmed it persisted through a fresh fetch, added and deleted a throwaway item and confirmed the receipt total reconciliation banner recovered — then reverted the rename to leave the seed data as found.
- **2026-07-29 — Tax/IVA proration in vision extraction.** Bug: receipts with an explicit tax/IVA line (e.g. `bills/bill2.jpg`: 80.00 + 55.00 pre-tax, 10% IVA = 13.50, real total 148.50) were extracted with items summing only to the pre-tax subtotal (135.00), silently losing the tax amount from the group's balance — nobody ever got charged for it. Fixed entirely inside `vision.py` (no schema/migration, no changes to the `event_balances`/`overall_balances` SQL views): the extraction prompt now also detects a `tax_amount`, which is prorated proportionally into the returned item prices before they're ever saved (`_apply_tax_proration`), so `items.price` already reflects what the group owes, tax included. The original detected `tax_amount` is preserved separately (`ExtractionResult.tax_amount`, threaded through `POST /receipts/{id}/extract` via `main.py`) purely so the frontend can show a transparency note ("IVA detected: X, already included above") in `ExtractionReview.jsx`. Verified live end-to-end against the real `bill2.jpg` photo (real OpenAI call): extracted items `[88.0, 60.5]`, `tax_amount: 13.5`, `receipt_total: 148.5`, no warnings — exact match. Tests: `tests/test_vision_extraction.py` grew from 39 to 49 cases (proration math, rounding-remainder edge case, warning-threshold change from 0.7→0.9 of `receipt_total` now that tax is prorated in before the mismatch check runs); full suite 100 passed.

### Phase 2 task plan

| Task | Description                                                                                                                                                                                                     | Main subagent            | Status     |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | ---------- |
| 0    | OpenAI setup: account, billing, monthly spend limit, `OPENAI_API_KEY` in `.env`, `uv pip install openai`, minimal verification call                                                                             | — (human)                | ✅ Done    |
| 1    | Isolated vision extractor (standalone script): real receipt photo → JSON of items. Tune the prompt without touching Phase 1 code                                                                                | vision-agent             | ✅ Done    |
| 2    | Data contract: Pydantic-validated JSON matching the `items` table (description, price, quantity); handle malformed JSON, total mismatch, missing fields                                                         | vision-agent             | ✅ Done    |
| 3    | Endpoint `POST /receipts/{id}/extract`: reads the already-uploaded image, calls the extractor, returns proposed items **without persisting**. No own sync connection; reuse `db.py` only to read the image path | vision-agent + api-agent | ✅ Done    |
| 4    | Frontend: extracted items **pre-fill** the existing `ItemCapture` form; 100% manual capture stays available                                                                                                     | ui-agent                 | ✅ Done    |
| 5    | Errors & fallback: API down / unreadable image / invalid JSON → clean fall back to manual capture with a clear message. Never breaks the Phase 1 flow                                                           | vision-agent             | ✅ Done    |
| 6    | Tests: parser/validator with **mocked** API responses (never the real API in tests). Good and bad cases                                                                                                         | test-agent               | ✅ Done    |
| 7    | Small logic & FE/BE improvements: delete participants and events from the app, plus a "delete all data" reset button in Balances. Strictly additive; more small improvements land here as they come up            | db + api + ui + test     | ✅ Done    |
| 8    | Phase 2 Definition of Done: real photo → pre-filled extraction → correct → save → correct balances, with fallback verified                                                                                      | — (human)                | ✅ Done    |

### Phase 2 progress log

Completed on 2026-07-13 (Tasks 0–1):

- [x] **Task 0 (human + verified by orchestrator):** `OPENAI_API_KEY` present and well-formed in `.env`; `openai==2.45.0` installed in the venv and pinned in `requirements.txt`; live `models.list()` call authenticated OK (123 models, vision-capable models available).
- [x] **Task 1 (vision-agent):** `vision_extract_experiment.py` — standalone throwaway script (isolated: no Phase 1 imports, no Turso connection) that base64-encodes a receipt photo, calls `gpt-4o` chat completions with `response_format={"type": "json_object"}`, and prints raw JSON. Test image: `bills/bill_example.jpg` (real Domino's tax invoice). Output matched the receipt exactly across two runs: Capsicum 99.0 ×1, Onion 99.0 ×1, Gold Corn 398.0 ×2 (merged from two 199.00 lines), `receipt_total` 603.3.
- **Prompt learnings (feed into Task 2):** the prompt must (a) merge duplicate lines with identical description + unit price into one item with quantity > 1, (b) strip the leading quantity number from descriptions, (c) exclude header/GSTIN/tax/total/footer lines, (d) return a `receipt_total` field as a tax-inclusive sanity-check reference — item prices will NOT sum to it when the receipt has tax lines. Task 2's mismatch check must account for tax, not assume `sum(items) == receipt_total`.
- **Incident (recovered):** `CLAUDE.md` had been accidentally renamed to `bi.md` in the working tree (likely a stray keystroke); detected via `git status` and restored with a rename back. No content lost.

Completed on 2026-07-13 (Tasks 2–3):

- [x] **Task 2 (vision-agent):** `vision.py` — production extractor module with the Pydantic data contract. Public API: `extract_receipt_items(image_path) -> ExtractionResult`; models `ExtractedItem` (description min_length=1, price gt=0, quantity ge=1 default 1 — field names match the `items` table) and `ExtractionResult` (items min_length=1, receipt_total gt=0, warnings list); `ExtractionError` with end-user-safe messages for every failure mode (missing/unreadable image, any OpenAI SDK error, empty response, non-JSON output, contract violation). Total mismatch is a **warning, never an error** (tax-aware: warn if `sum(items) > receipt_total`, or if it's below 70% of it) — suspicious data flows through flagged; the human reviewer always decides. Prompt carried over from Task 1 with all learned rules, generalized. MIME type detected from extension. No Phase 1 imports, no Turso connection, persists nothing. Live smoke run reproduced the Task 1 numbers exactly (Capsicum 99×1, Onion 99×1, Gold Corn 398×2, total 603.3, no warnings).
- [x] **Task 3 (api-agent):** `POST /receipts/{receipt_id}/extract` in `main.py` (strictly additive: two new response models + one endpoint, nothing else touched). Reads `image_path` via the existing `db.get_receipt_with_items` (no new db functions, no own connection), calls `vision.extract_receipt_items`, returns `{receipt_id, items[], receipt_total, warnings[]}` **without persisting** — saving still goes through Phase 1 `POST /receipts/{id}/items` after human review. Status mapping: 404 unknown receipt, 422 empty `image_path` sentinel (no image → manual capture), 502 with the user-safe message on `ExtractionError`. Verified live end to end: real upload → extract 200 with correct items → `GET /receipts/{id}` still shows zero items (non-persistence proven) → 404 and 502 paths exercised → temp fixtures cleaned up, seed balances intact (Ana +70, Bruno −55, Carla −15).
- [x] **Fresh-context adversarial review before commit** — two confirmed findings, both fixed and verified: (1) JSON `Infinity` passed `gt=0` and was serialized as `null` by FastAPI's encoder, breaking the non-nullable float contract → `allow_inf_nan=False` added to `price` and `receipt_total` (NaN was already rejected by `gt=0`); (2) `.heic` (default iPhone photo format) and `.pdf` — both on the Phase 1 upload allow-list — were silently mislabeled as `image/jpeg` in the data URL, producing a misleading generic 502 → now rejected up front by `_guess_mime_type` with an honest "format not supported" message; unknown extensions still default to jpeg.
- **Gotcha (test invocation):** bare `uv run pytest` fails with `ModuleNotFoundError: No module named 'db'` (no `pythonpath` config in the repo); use `uv run python -m pytest` (adds cwd to `sys.path`). Pre-existing, not a Phase 2 regression.
- **Gotcha (live behavior):** the first extraction call in a session can hit a transient upstream failure → clean 502; an immediate retry succeeded. Expect this in manual testing; no code change needed.

Completed on 2026-07-14 (Task 4):

- [x] **Task 4 (ui-agent):** extraction pre-fill UI. New `frontend/src/components/ExtractionReview.jsx` rendered in `ReceiptDetail.jsx` above the manual "Add an item" block: an "Extract items from photo" button calls the new `api.js` `extractReceiptItems()` (`POST /receipts/{id}/extract`), then shows an editable proposal table — description and price editable per row, quantity read-only (the Phase 1 save endpoint has no quantity field; price already carries the line total, so balances are unaffected — explained in a hint), row remove buttons, `receipt_total` reference, and every extraction warning displayed. "Add N items to receipt" saves via the EXISTING `addItems()` (Phase 1 endpoint, `[{name, price}]`), then refreshes the Phase 1 item list; "Discard" resets. Extraction errors (404/422/502) show the API's user-safe message plus a "manual capture below still works" line, with retry available. Manual `ItemForm`, item list, and assignment flow untouched. Build clean.
- [x] **Fresh-context adversarial review before commit** — one CRITICAL confirmed and fixed: `POST /receipts/{id}/items` inserts sequentially (each item commits + pushes individually), so a mid-list failure can persist earlier rows; the UI kept the full proposal, so a retry would duplicate the already-saved rows and corrupt balances. Frontend fix (Phase 1 endpoint untouched, per the additive constraint): on save failure the component now refreshes the real item list and shows a "save may have partially succeeded — check the list and remove already-added rows before retrying" hint. Also added `aria-label`s to the row inputs (accessibility nit from the same review). Reviewer explicitly ruled out: double-click races (state flips before the first `await`), stale state across receipts (component unmounts on back-navigation), discard/re-extract residue, empty-items and price-format edge cases.

Completed on 2026-07-15 (Task 5):

- [x] **Task 5 (vision-agent):** errors & fallback hardening. Orchestrator audit first: Tasks 2–4 already covered every *erroring* failure mode (missing/unreadable/unsupported image, any SDK error, empty/non-JSON/contract-violating output → user-safe `ExtractionError` → 502 → UI message + "manual capture below still works" + retry). The one confirmed gap was the *hanging* API: `OpenAI()` used SDK defaults (600 s timeout, 2 retries) — a stalled API could block extraction for ~20 minutes. Fix in `vision.py` only: `OpenAI(timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS=60, connect=CONNECT_TIMEOUT_SECONDS=5), max_retries=1)` plus a dedicated `APITimeoutError` catch (before the broad except) with its own user-safe message ("took too long to respond — try again, or use manual item capture").
- [x] **Fresh-context adversarial review before commit** — one CONFIRMED regression caught and fixed: the first iteration passed a bare float (`timeout=60.0`), which sets ALL httpx phases to 60 s — silently widening the connect timeout from the SDK default 5 s to 60 s, making an unreachable host *slower* to fail. Fixed with an explicit `httpx.Timeout(60, connect=5.0)`. Reviewer verified against installed openai 2.45.0: `APITimeoutError` is top-level, raised on all `httpx.TimeoutException` subtypes, and correctly ordered before the broad except; connection-refused/DNS errors still get the unchanged "unavailable" message.
- **Verified live (simulated failures, no mocks committed):** black-holed host (`OPENAI_BASE_URL` → unroutable IP) fails in **10.6 s** (5 s connect × 2 attempts) with the timeout message; local accept-but-never-respond server fails in 2 × read-timeout with the same message; connection refused fails in 0.6 s with the "unavailable" message; nonexistent/directory image paths fail instantly. Happy-path live call unchanged (Capsicum 99×1, Onion 99×1, Gold Corn 398×2, total 603.3). Full suite: 44 passed. Worst-case bounded wait is now ~2 × 60 s + backoff (stalled-but-connected API), vs ~20 minutes before.

Completed on 2026-07-15 (Task 6):

- [x] **Task 6 (test-agent):** `tests/test_vision_extraction.py` — 39 new tests, all with the OpenAI API mocked at the Python level (`vision._call_openai`, `vision.OpenAI` itself, or `vision.extract_receipt_items` as seen by `main` for the endpoint tests). Suite total: **83 passed** (44 existing untouched + 39 new). Coverage: `_parse_and_validate` good/bad cases (non-JSON, wrong shapes, empty items, `Infinity` price via `allow_inf_nan=False`, quantity 0, quantity default); `_apply_total_warnings` (both warnings + exact-boundary no-warning cases); `_guess_mime_type` (accepted types, .heic/.pdf rejection, jpeg default); `extract_receipt_items` short-circuits before any API interaction on missing/directory paths (mock asserted NOT called); both `_call_openai` exception branches (`APITimeoutError` → "took too long", generic → "unavailable") plus empty-response; endpoint 404/422/502/200 including non-persistence (GET after extract shows zero items).
- [x] **No-network guarantee proven two ways:** an autouse fixture strips `OPENAI_API_KEY` for every test in the file (defense-in-depth — any un-mocked call fails on auth), and the full suite passes identically with the key removed from the environment (`env -u OPENAI_API_KEY`).
- [x] **Fresh-context adversarial review before commit** — verdict commit-ready, zero confirmed defects. The reviewer mutation-tested the four highest-risk assertions against scratch copies (removed `allow_inf_nan=False`, removed the `isfile` guard, collapsed the `APITimeoutError` branch, removed the endpoint's except) and every corresponding test failed — proving the tests are not vacuous. Mock seams verified live (`main.py` does `import vision` + attribute lookup at call time, so patching `main`'s `vision` module object is the real seam). Two optional nits (docstring seam precision, 422 test asserting only the status code) polished before commit; suite re-run green.
- **Deliberately out of scope:** `_encode_image_b64`'s OSError branch is shadowed by the `os.path.isfile` guard for nonexistent/directory paths (only reachable via e.g. a permission-denied file) — noted, product code left untouched. No live-API integration test, per the hard rule; the live path was already smoke-verified in Tasks 2–5.

Completed on 2026-07-15 (Task 7 — delete participants/events + full data reset):

- [x] **db-agent (`db.py`):** new `clear_all_data()` — destructive full reset. Deletes every row from all tables in FK-safe order (`item_assignments → items → receipts → event_participants → events → participants`), then `commit()` + `push()`, following the existing explicit-cascade pattern (pyturso has `PRAGMA foreign_keys` OFF, so ON DELETE CASCADE never fires). Idempotent. No schema/migration change. Existing `delete_*` helpers untouched.
- [x] **api-agent (`main.py` + `services.py`):** three new DELETE endpoints, strictly additive (no existing endpoint/model/CORS touched). `DELETE /participants/{id}` → 204, with an **inline** error mapping (does NOT alter the shared `value_error_to_http`): "does not exist" → 404, financial-history guard "cannot be deleted" → **409** with the message as detail. `DELETE /events/{id}` → 204, cascade handled inside `db.delete_event`, 404 if unknown. `DELETE /data` → 200 `{"status":"all data deleted"}`, calls `db.clear_all_data()` then a new `services.clear_upload_dir()` (unlinks only regular files inside `uploads/`, leaves the dir; idempotent) so no orphaned image files remain.
- [x] **ui-agent (`frontend/`):** per-row Delete button in `ParticipantsPage` and `EventsPage` (both behind `window.confirm`; the event confirm warns about cascading receipt/item removal); a visually separated "danger zone" Delete-all-data button in `BalancesPage` behind a strong confirm, which refetches events + overall balances afterward (view goes empty) and shows a success message. `api.js` gained `deleteParticipant`/`deleteEvent`/`deleteAllData` (204 bodies handled, 409 `detail` surfaced via `StatusMessage`). Minor `styles.css` additions (`.btn--danger`, `.danger-zone`). `ItemList.jsx` deliberately left alone (unrelated pre-existing edit). `npm run build` clean (verified by orchestrator).
- [x] **test-agent (`tests/test_deletes.py`, new file):** 7 additive tests, offline fixtures matching `test_api_flow.py`. Suite total **90 passed** (83 existing untouched + 7 new; `git diff --stat tests/` empty). Covers: participant 204/no-history + gone; both guard paths (payer and assignment) → 409 + survives; unknown → 404; event cascade 204 (event/receipts/items/assignments all 404, participants survive); unknown event 404; `DELETE /data` → 200 with participants/balances/events all empty and `uploads/` emptied.
- **Design decision (yours):** participant deletion RESPECTS the Day 3 history guard — a participant who paid a receipt or has item assignments returns 409 and is never deleted; the ledger stays consistent. The full reset is the explicit escape hatch for wiping everything.
- **Flag (not blocking):** `DELETE /data` has no auth beyond the UI confirm — any client reaching the API can wipe all data with one request. Acceptable for this local dev phase; revisit if the app is ever exposed beyond localhost.

Completed on 2026-07-16 (Task 7 — frontend UX & visual improvements, all additive, no backend/schema change):

- [x] **In-app guide (`GuideSteps.jsx`, new):** collapsible "How it works" roadmap of the 7-step flow (add participants → pick event → add them to it → upload receipt with who-paid + total → list products/prices → split each → see per-person balance), rendered under the header. After a codebase analysis confirmed `who paid + total` is the "paid" side of `event_balances`, it stays an explicit step.
- [x] **Reconciliation made prominent (`ReceiptDetail.jsx`):** items-vs-total hint became a clear `.reconcile` block (match / mismatch states, not color-alone, `aria-live` on mismatch). Fixed a latent bug: `itemsSum` multiplied `price × quantity`, but `items.price` is already the full line total (quantity is informational; the balance view never multiplies by quantity) — now sums price only.
- [x] **Delete-all feedback (`BalancesPage.jsx`, `StatusMessage.jsx`):** the "danger zone" now hides once there is no data left, and the success message moved out of that block (so it survives the block disappearing) using a new high-contrast `success` StatusMessage variant.
- [x] **Modern fintech redesign (`styles.css` rewrite, `index.html`, `App.jsx`):** dropped the ledger/ruled-paper look. Single teal accent (#0F766E), slate background, white cards separated by whitespace + soft shadow (no ruled/dotted lines), Inter with tabular-nums for money, larger/bolder headings, segmented tab control, pill balance badges, and a few purposeful transitions (row hover-lift, button press, expand fades) all guarded by `prefers-reduced-motion`. Class names kept intact (restyle-in-place) — verified no JSX class lost its rule.
- [x] **Name normalization (`utils.js` `toTitleCase`, `ParticipantsPage.jsx`, `EventsPage.jsx`):** participant and event names are title-cased on create (each word capitalized) so stored data reads consistently everywhere (UI, balances, MCP). Normalized on write in the frontend — endpoints untouched.
- [x] **Participant row alignment (`styles.css`):** the "joined …" dates now stay in a right-aligned column (name takes the flexible space) instead of drifting horizontally with name length.

Completed on 2026-07-29 (Task 7 — translated backend error/warning messages, additive, frontend-only):

- [x] **ui-agent (`frontend/src/i18n/apiMessages.js`, new; `en.js`/`es.js` extended; 9 components wired):** backend `detail`/`warnings[]` strings were the last untranslated surface after the 2026-07-17 i18n rollout. `apiMessages.js` pattern-matches the exact backend wording (character-for-character, verified live against `main.py`/`vision.py`) onto new `apiErrors.*`/`apiWarnings.*` keys, translated at render time so an on-screen message re-translates if the language is switched afterwards. Backend untouched (Phase 1/2-frozen). `npm run build` clean. Commit `f69604a`.

Completed on 2026-07-29 (Task 8 — Phase 2 Definition of Done, verified live end-to-end):

- [x] **Verified live** with `uvicorn main:app` + `vite` dev server, against a real receipt photo (`bills/bill.jpeg`, the same Chiringuito receipt used in the earlier Task-2/3 smoke tests): `POST /receipts/{id}/extract` (live `gpt-5.6-luna` call) returned CHEESEBURGER SIMPLE price=7.0 qty=2, MITI-MITI price=5.0 qty=2, `receipt_total`=12.0, no warnings — reproducing the earlier verification exactly. Saved both items as-is through the existing `POST /receipts/{id}/items` (Phase 1 endpoint, unmodified), split 50/50 between two throwaway test participants, then confirmed `GET /events/{id}/balances` computed correctly through the unmodified `event_balances` view: total_consumed 6.0 each, net balances +94/-6 (payer total_paid 100 minus 12 consumed, split evenly) — no new balance logic involved.
- [x] **Fallback path verified live (not just mocked):** uploaded a `.pdf` (on the Phase 1 upload allow-list but not supported by extraction) and called `/extract` on it — got a clean 502 with the exact user-safe message ("This file format is not supported by automatic extraction..."), matching `apiErrors.extraction.unsupportedFormat` word-for-word. Manual item capture (`POST /receipts/{id}/items`) immediately succeeded afterward on the same receipt, proving the fallback never blocks Phase 1 capture.
- [x] **No Phase 1/2 regression:** all verification done through existing endpoints/views with zero code changes; test data (1 event, 2 participants, their receipts/items/assignments) deleted afterward via the Task 7 delete endpoints — seed data (Ana/Bruno/Carla/Joel, Asado sabado, Dia de playa, Nuevo evento) confirmed untouched.
- **All 6 Phase 2 DoD checklist boxes can now be marked done** (see below). Phase 2 is functionally complete.

Confirmed by the user on 2026-07-29: both remaining human-only checks are done — the Task 7 EN/ES switcher click-through, and the inherited Phase 1 live MCP chat test ("¿cuánto debe cada quien en total?" from inside Claude Code). **The application is now complete end to end.**

Completed on 2026-07-17 (Task 7 — frontend internationalization EN/ES, additive, frontend-only):

- [x] **ui-agent (`frontend/src/i18n/`, new):** custom lightweight i18n layer, zero new npm dependencies. `en.js` + `es.js` (137 dot-namespaced keys each, verified parity), `LanguageContext.jsx` — `LanguageProvider` + `useTranslation()` hook with `t(key, vars)`, `{placeholder}` interpolation, English fallback for missing keys. Language persisted in localStorage (`recibosplit.language`); first visit detects `navigator.language` (es\* → es, else en).
- [x] **Language switcher (`App.jsx`):** globe-icon toggle button (inline SVG) in the header showing EN/ES, translated `aria-label`/`title`, styled to the fintech design (`.language-switcher` in `styles.css`).
- [x] **All 13 components externalized** — every user-facing string, `window.confirm()` dialog, placeholder, and `aria-label` goes through `t()`; `formatDate(value, language)` localizes dates (en-US / es-ES). Backend-originated messages (API error `detail`, extraction `warnings[]`) are deliberately shown as-is, untranslated — translating them would touch Phase 1 endpoint behavior. Spanish register: neutral "tú", no regional slang.
- [x] **Fresh-context adversarial review:** commit-ready, zero confirmed defects (key parity, all `t()` call sites incl. dynamic keys, interpolation vars in both dictionaries, confirm guards, aria wiring, no logic drift, `npm run build` clean re-verified by the reviewer).
- [x] **Human check confirmed 2026-07-29:** visual click-through of the switcher (toggle EN↔ES across all tabs).
- **INCIDENT (resolved 2026-07-17):** the working copy had lost `.git`, `.gitignore`, and `.mcp.json` (folder copied/recreated dropping dotfiles). The user confirmed the old history is unrecoverable. Repository reinitialized: `.gitignore` recreated first (protects `.env`, `recibosplit.db*`, `recibosplit_mcp.db*`, `uploads/`, venv/node_modules/build dirs), `.mcp.json` recreated with the documented absolute paths (venv python verified), then root commit `cb7e5db` snapshotting the full project including the i18n work. Old commit hashes referenced earlier in this file no longer exist. **No remote is configured — until one is added, this repo has a single point of failure again.**

### Phase 2 Definition of Done

Phase 2 is done when, with a **real receipt photo**:

- [x] Uploading a receipt and requesting extraction pre-fills the item form with sensible description/price/quantity values (verified live 2026-07-29, `bills/bill.jpeg`)
- [x] The human can edit any extracted row before saving; saving goes through the existing Phase 1 capture endpoints (extraction persists nothing on its own) — non-persistence proven in Task 3, save-through-Phase-1 proven live in Task 8
- [x] After saving, balances compute through the same Phase 1 views — no new balance logic was introduced (verified live 2026-07-29: `event_balances` view, exact expected numbers)
- [x] Every failure mode (API error, unreadable image, malformed JSON, price/total mismatch) falls back to manual capture with a clear message, and manual-only capture still works end to end (unsupported-format fallback verified live 2026-07-29; other failure modes covered in Tasks 2–6 live smoke tests + mocked test suite)
- [x] `test-agent` suite passes with mocked API responses; no test makes a real OpenAI call (83 passed; proven with `OPENAI_API_KEY` removed from the environment)
- [x] No Phase 1 schema, view, endpoint behavior, or existing test changed (Task 8 verification used only existing endpoints/views, zero code changes)

---

## Phase 1 log (complete — kept for history)

### Day 7 — Tests + polish ✅ (week plan complete)

Completed on Day 7 (2026-07-13):

- [x] `db.py` (db-agent): **local-only mode** — without `TURSO_DATABASE_URL`/`TURSO_AUTH_TOKEN` in the env, `init_db()` opens a plain `turso.connect()` on `RECIBOSPLIT_DB_PATH` and `push()`/`pull()` become no-ops (patched on the connection instance — zero call-site changes). `close_db()` added so tests can re-point at fresh temp files. `load_schema(conn)` helper added — **required** because pyturso 0.6.1's `executescript()` has a UTF-8 byte-offset bug triggered by the Spanish comments in `schema.sql` (strips `--` comments before executing). `list_event_receipts(event_id)` read function added.
- [x] `main.py` (api-agent): `GET /events/{event_id}/receipts` (closes the Day 5 known gap) — verified live: seeded receipt with payer_name "Ana", total 90; 404 on unknown event.
- [x] `frontend/` (ui-agent): `EventDetail.jsx` now fetches the persistent receipt list from the new endpoint (parallel fetch on mount, refetch after upload) — receipts survive reloads; session-local workaround removed. `api.js` gained `getEventReceipts()`. Build clean.
- [x] **pytest suite (test-agent): 44 passed, 0 failed** — `tests/` with offline fixtures (temp db per test, Turso env popped after `import db`, `db.load_schema()`, uploads isolated via tmp cwd). Coverage: validate_shares incl. tolerance boundary; assign_item (replace semantics, duplicates, share ≤ 0, non-member, missing item); create_receipt payer invariant; delete_participant history protection; **full acceptance scenario at BOTH layers** (db.py and HTTP API) asserting the exact DoD numbers; error paths (422/404); receipts listing. Re-run by orchestrator: 44 passed in 0.26s.
- Documented view semantics (asserted in tests): event with participants but no receipts → one all-zero row per participant (COALESCE), not empty; participants never linked to any event are absent from `overall_balances`.
- Test-env gotchas (documented in `tests/conftest.py`): pop Turso env vars AFTER `import db` (module-level `load_dotenv()` repopulates otherwise); never `executescript()` raw `schema.sql` (UTF-8 bug above).
- Not covered (deliberate, framework-level or stretch): delete cascades, `GET /receipts/{id}` direct, `GET /items/{id}/assignments` direct, empty-name Pydantic validation.

Completed on Day 6 (2026-07-10):

- [x] `db.py`: local replica path made configurable via `RECIBOSPLIT_DB_PATH` env var (default `recibosplit.db`), config-only change inside `init_db()` — no SQL changed.
- [x] `mcp_server.py` created (api-agent): read-only MCP server using the official SDK (`mcp==1.28.1`, stable v1.x API — `from mcp.server.fastmcp import FastMCP`, `@mcp.tool()`, `mcp.run()` over stdio). Sets `RECIBOSPLIT_DB_PATH=recibosplit_mcp.db` (its own replica) at the top of the file, before `import db`, so it never contends for `recibosplit.db`'s exclusive `turso.sync` file lock. 5 tools, each calling straight into `db.py` (no SQL in this file): `list_participants`, `list_events`, `get_event_balances(event_id)`, `get_overall_balances()`, `get_receipt_details(receipt_id)`. Every tool calls `db.get_db().pull()` first so answers reflect the latest remote state (writes come from the separate FastAPI process). `ValueError`s (unknown event/receipt) are caught and returned as `{"error": ...}` instead of crashing the server. No write tools, per Phase 1 scope.
- [x] `.mcp.json` created at project root registering the `recibosplit` server for Claude Code (absolute paths to `.venv/bin/python` and `mcp_server.py`).
- [x] `.gitignore` extended: `recibosplit_mcp.db` / `recibosplit_mcp.db-*` added (the existing `recibosplit.db*` pattern did not match the new filename). Verified with `git check-ignore -v` — all 4 replica-related files ignored.
- [x] Verified end-to-end with a throwaway stdio client (scratchpad, not committed): listed all 5 tools, called `get_overall_balances`, `get_event_balances` for "Asado sabado" (resolved via `list_events`), and `get_receipt_details` for its seeded receipt. Numbers matched the Definition-of-Done table exactly: Ana 90/20/+70, Bruno 0/55/-55, Carla 40/55/-15; per-event Ana +70/Bruno -35/Carla -35; receipt items (Carne 1/3 each, Bebidas 1/2 Bruno+Carla) confirmed.
- [x] **Lock-conflict proof:** ran `uvicorn main:app` (against `recibosplit.db`) and the MCP stdio client (against `recibosplit_mcp.db`) at the same time — both answered correctly with no lock error. `uvicorn` was stopped afterwards; no stray processes remained.
- **Gotcha (new, worth remembering):** the _first_ `pull()` against a brand-new replica file (i.e. the very first time `recibosplit_mcp.db` is created) takes roughly 60 seconds — it's a full initial sync, not a hang. Subsequent pulls against the same file are fast. Don't mistake this for a bug if the MCP server seems slow to answer its very first query after a fresh checkout.
- **Gotcha (MCP SDK behavior):** a tool that returns `list[dict]` gets serialized by FastMCP as **structured content** wrapped as `{"result": [...]}` (MCP 2025-06-18 structured-output spec — plain arrays aren't valid top-level structured output), not as one JSON-array text block. Client code should read `CallToolResult.structuredContent["result"]` rather than assuming `content[0].text` is a JSON array.

Completed on Day 5 (2026-07-09):

- [x] Day 5 prerequisite (api-agent): `GET /events/{event_id}/balances` and `GET /balances` endpoints added to `main.py` (thin wrappers over the Day 4 `db.py` view reads, Pydantic response models) + `CORSMiddleware` for the Vite dev origins. Verified via API: overall balances exactly Ana 90/20/+70, Bruno 0/55/-55, Carla 40/55/-15; 404 on unknown event; CORS preflight OK.
- [x] React frontend built (ui-agent) under `frontend/`: Vite 8 + React 19, plain JS/JSX, local state only (`useState`), no router/state/fetch/UI libraries. 12 components: tabs (Participants / Events / Balances), event detail with add-participant, multipart receipt upload (image + payer + total), item capture with running-sum-vs-total hint, per-item assignment editor with even-split helper and client-side share-sum hint (server authoritative, 422 `detail` surfaced), balances views (per event + overall) with green/red owed/owes badges. All fetch calls centralized in `src/api.js`; API errors always displayed.
- [x] Verified by orchestrator: `npm install` + `npm run build` clean (0 vulnerabilities, 30 modules); live smoke test with uvicorn + Vite dev — UI served, API responded with correct CORS header and exact acceptance numbers. Both servers stopped after.
- Design: accounting-ledger aesthetic (ruled lines, mono/typewriter type, black-ink credit / red-ink debit), single stylesheet. Google Fonts loaded at runtime via `<link>` (no build-time network dependency).
- **Known gap (workaround in place):** no `GET /events/{id}/receipts` endpoint exists — `EventDetail.jsx` keeps receipts created in the current session in local state so item capture stays reachable. Add the endpoint (api-agent) and swap the component to fetch it — candidate for Day 6/7.
- **Not yet checked off:** the Phase 1 checklist item "complete the full flow via the UI" still needs a human click-through in the browser (`uvicorn main:app` + `npm run dev`).

Completed on Day 4 (2026-07-08):

- [x] `db.py` extended (db-agent): `get_event_balances(event_id)` — plain SELECT from the `event_balances` view joined to `participants` for names, raises `ValueError` if the event doesn't exist; returns `[{participant_id, participant_name, total_paid, total_consumed, net_balance}, ...]`. `get_overall_balances()` — plain SELECT from `overall_balances` joined to `participants`, returns `[{participant_id, participant_name, total_paid_all_events, total_consumed_all_events, total_net_balance}, ...]`. Zero arithmetic in Python; both views used as-is.
- [x] `seed_test_data.py` extended: now seeds Event 2 "Dia de playa" (Bruno + Carla, receipt paid by Carla for $40, item "Snacks" split 1/2 each) in addition to Event 1, idempotent for both events independently.
- [x] Acceptance scenario validated end-to-end: `overall_balances` matches the Definition-of-Done table **exactly** — Ana 90/20/+70, Bruno 0/55/-55, Carla 40/55/-15 — net balances sum to 0.0. No view or schema changes were needed.
- **Bug found and fixed in `seed_test_data.py`'s idempotency cleanup:** the Day 1 version relied on `ON DELETE CASCADE` firing when deleting an event row, but per the documented gotcha `PRAGMA foreign_keys` is OFF by default on pyturso connections — cascades do not fire automatically. The cleanup now deletes `item_assignments` → `items` → `receipts` → `event_participants` → `events` explicitly, matching the pattern already used in `db.py`'s `delete_event()`. Verified by re-running the seed twice in a row: remote item counts stayed constant (no orphaned duplicates accumulating).
- **Schema decision:** `receipts.image_path` is `TEXT NOT NULL`, so Event 2's "no image" receipt uses `""` (empty string) as an explicit sentinel rather than a fake path or a schema change. If "no image" becomes a recurring product case (not just a seed fixture), `image_path` should be made nullable via a numbered migration + `schema.sql` update at that point — not needed for Phase 1.
- No new migration was needed; `schema.sql` is unchanged.

Completed on Day 3 (2026-07-08):

- [x] `db.py` extended (db-agent): `assign_item(item_id, assignments)` with **replace semantics** (atomic delete + insert + push); reusable `validate_shares` helper (sum to 1.0, 1e-6 tolerance); validations for duplicates, share > 0, membership of each participant in the item's event. `get_item_assignments()` added; `get_receipt_with_items()` items now include assignments (single joined query, no N+1).
- [x] Delete helpers added (pending from Day 2): `delete_item/receipt/event/participant` — `delete_participant` refuses if the participant has financial history (paid receipts or assignments).
- [x] `main.py` extended (api-agent): `PUT /items/{item_id}/assignments` (replace semantics, returns resulting assignments) and `GET /items/{item_id}/assignments`; `ItemOut` now nests assignments in receipt responses.
- [x] Smoke-tested live: happy path, replacement verified, 422 on bad share sum / participant-not-in-event, 404 on unknown item. All temp rows cleaned via the new delete helpers; Day 1 seed intact (balances still Ana +70 / Bruno -35 / Carla -35).
- **Gotcha (critical, documented in `db.py`):** `PRAGMA foreign_keys` is OFF by default on pyturso connections — `ON DELETE CASCADE` in `schema.sql` does NOT fire. Delete helpers cascade explicitly in SQL instead of relying on the pragma (per-connection, not persisted).
- **Gotcha:** `turso.sync` holds an exclusive file lock on `recibosplit.db` — only ONE process can use the local replica at a time (uvicorn had to be stopped before running the cleanup script). Relevant for the Day 6 MCP server design.

Completed on Day 2 (2026-07-08):

- [x] `db.py` created (db-agent): shared pyturso sync connection (`init_db`/`get_db`), write functions (`create_participant`, `create_event`, `add_participant_to_event`, `create_receipt`, `add_item` — each commits then `db.push()`), read functions (`list_participants`, `list_events`, `get_event_with_participants`, `get_receipt_with_items`). FK checks raise `ValueError`; enforces payer-must-be-event-participant invariant.
- [x] `main.py` created (api-agent): FastAPI app with 9 endpoints — participants CRUD-lite, events, add-participant-to-event, **multipart image upload** (`POST /events/{id}/receipts` — stores file under gitignored `uploads/`, no OCR), **item capture** (`POST /receipts/{id}/items`, single item or list), receipt GET. Pydantic validation; `ValueError` mapped to 404/422 via `services.py`.
- [x] Smoke-tested live with uvicorn + curl: full flow (participant → event → link → image upload → items → GET) plus error paths (404s, 422 payer-not-in-event). Temp test rows deleted afterwards; Day 1 seed intact.
- [x] Deps installed with uv: fastapi, uvicorn, python-multipart
- Gotcha (documented in `main.py`): FastAPI 0.139 doesn't flatten a `Form()` Pydantic model next to an `UploadFile` — multipart scalar fields must be declared individually with `Annotated[..., Form()]`.
- Pending for Day 3: `db.py` has no `delete_*` helpers yet — add them when db-agent implements assignment functions.

Completed on Day 1 (2026-07-08):

- [x] `seed_test_data.py` created: seeds Event 1 of the acceptance scenario (Ana, Bruno, Carla, "Asado sábado", $90 receipt) with parameterized SQL
- [x] Full write + `db.push()` / `db.pull()` round trip validated against Turso Cloud — data confirmed remotely via a fresh sync connection
- [x] `event_balances` view verified: Ana +70, Bruno -35, Carla -35 (matches expected numbers exactly)
- [x] Script is idempotent (safe to re-run; reuses participants, recreates the event via `ON DELETE CASCADE`)
- Pattern established: validate that `item_assignments.share` sums to 1.0 in Python before insert — reuse this in the API layer (Day 2/3)

Completed on Day 0, before writing application code:

- [x] Defined Phase 1 scope (manual image upload, no automatic recognition)
- [x] `schema.sql` created: participants, events, event_participants, receipts, items, item_assignments + `event_balances` and `overall_balances` views
- [x] Subagents created in `.claude/agents/`: db-agent, api-agent, ui-agent, test-agent
- [x] `CLAUDE.md` created with project context and conventions

- [x] `.gitignore` created (protects `.env` and the local `recibosplit.db` replica file)
- [x] Turso CLI installed, logged in, database created, `schema.sql` loaded
- [x] `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` saved in `.env`
- [x] Connection verified with `verify_connection.py` — all 6 tables + 2 views confirmed synced locally

## Week plan complete. Both human-only Definition-of-Done items (UI click-through, live MCP chat test) confirmed done.

## Week plan

| Day | Task                                                              | Main subagent        | Status  |
| --- | ----------------------------------------------------------------- | -------------------- | ------- |
| 0   | Setup: schema + subagents + CLAUDE.md + Turso connection verified | —                    | ✅ Done |
| 1   | Load schema.sql into Turso, validate with test data               | db-agent             | ✅ Done |
| 2   | Image upload endpoint + item-capture form                         | api-agent            | ✅ Done |
| 3   | Item-to-participant assignment logic                              | db-agent + api-agent | ✅ Done |
| 4   | Multi-event balance calculation                                   | db-agent             | ✅ Done |
| 5   | React components: upload, capture, assign, view balances          | ui-agent             | ✅ Done |
| 6   | Package as an MCP server                                          | api-agent            | ✅ Done |
| 7   | Tests + polish                                                    | test-agent           | ✅ Done |

## Decision log

- **`pyturso` over the older `libsql` package** (updated this session): Turso now recommends `pyturso` for local/embedded use — a local SQLite file kept in sync with Turso Cloud via `turso.sync.connect(...)`, `db.pull()`, and `db.push()`. Since the backend runs as a persistent server (not stateless/serverless), the embedded-replica model gives faster reads. Remember: `db-agent` must call `db.push()` after every write commit.

- **Turso over Supabase/plain SQLite** (decided this session): remote, multi-device access is needed for participants; Turso provides that while keeping SQLite as the engine.
- **Manual item capture in Phase 1**: automatic vision-based recognition would require an API call to a vision-capable model, which was intentionally postponed. See `CLAUDE.md` → Phase 2.
- **Balances calculated in SQL (views), not in application code**: to prevent business logic from drifting out of sync between backend and frontend.

## Beyond Phase 2 (still out of scope)

- Debt simplification between participants (a "who pays whom directly" algorithm instead of just a net balance per person). Note: automatic vision recognition, previously listed here, is now the active Phase 2 above.

## Definition of Done — Phase 1

Phase 1 is NOT done just because code exists. It's done when this specific acceptance scenario produces the exact numbers below — run it manually (via the API or the UI) before checking anything off:

**Setup:**

- 3 participants: Ana, Bruno, Carla
- Event 1 "Asado sábado" — participants: Ana, Bruno, Carla
  - Receipt paid by **Ana**, total $90
    - Item "Carne" $60, split evenly among Ana/Bruno/Carla (share 1/3 each)
    - Item "Bebidas" $30, split evenly between Bruno/Carla only (share 1/2 each)
- Event 2 "Día de playa" — participants: Bruno, Carla (Ana not included)
  - Receipt paid by **Carla**, total $40
    - Item "Snacks" $40, split evenly between Bruno/Carla (share 1/2 each)

**Expected `overall_balances` result:**

| Participant | Total paid | Total consumed | Net balance |
| ----------- | ---------- | -------------- | ----------- |
| Ana         | 90         | 20             | **+70**     |
| Bruno       | 0          | 55             | **-55**     |

| Carla | 40 | 55 | **-15** |

(Net balances must sum to 0. If they don't, something in the assignment or view logic is wrong.)

**Checklist to confirm Phase 1 is complete:**

- [x] All endpoints from `api-agent.md` implemented and manually tested with the scenario above (smoke-tested live on Days 2–7; full flow also covered by `tests/test_api_flow.py`)
- [x] The numbers above match exactly (down to the cent) when queried via the API (verified live on Day 5/6 and asserted in `tests/` at both the db and API layers)
- [x] React UI: you can complete the full flow (upload image → add items → assign → view balances) without touching the database directly — verified end-to-end on 2026-07-13 with real browser automation (agent-browser): participant created via form, receipt image uploaded via the UI, item captured, assigned via even-split, balances updated correctly (Diego +25 / Elena −25 test scenario); temp data cleaned up afterwards, seed balances intact
- [x] `test-agent`'s pytest suite passes, including edge cases (shares not summing to 1.0, participant not in event, event with no receipts) — 44 passed
- [x] MCP server responds correctly in the Claude Code chat to a question like "¿cuánto debe cada quien en total?" — protocol path proven with an SDK stdio client on Day 6; **live chat test confirmed done by the user on 2026-07-29**
- [x] `git log` shows incremental commits per day (not one giant commit at the end) — one `feat` commit per day, Day 1 through Day 7

Only when every box above is checked is Phase 1 truly done — not before.

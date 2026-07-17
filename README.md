# ReciboSplit

Split group expenses from a receipt photo — like Splitwise, but self-hosted. Upload a receipt image, type in each line item, assign items to the people who consumed them, and the app tracks who owes whom across multiple events. It also ships as an MCP server, so you can ask Claude Code questions like "who owes what?" in plain language.

**Stack:** FastAPI (Python) · Turso (SQLite-compatible cloud DB) · React + Vite · MCP.

## Quick path

Already set up? This is all you need:

```bash
# Terminal 1 — backend API on http://localhost:8000
.venv/bin/uvicorn main:app --port 8000

# Terminal 2 — frontend on http://localhost:5173
cd frontend && npm run dev
```

Open http://localhost:5173 and you're in. First time here? Do the setup below once, then come back to these two commands.

## Prerequisites

| Tool | Why | Install (macOS) |
| --- | --- | --- |
| [uv](https://docs.astral.sh/uv/) | Python env + packages | `brew install uv` |
| Node.js 20+ | Frontend (Vite + React) | `brew install node` |
| [Turso CLI](https://docs.turso.tech/cli) | Create the cloud database | `brew install tursodatabase/tap/turso` |
| A Turso account | Free tier is enough | created during `turso auth login` |

## One-time setup

### 1. Create the database

```bash
turso auth login                          # opens the browser
turso db create recibosplit
turso db shell recibosplit < schema.sql   # load the tables and views
```

### 2. Create `.env` with your credentials

```bash
turso db show recibosplit --url           # -> TURSO_DATABASE_URL
turso db tokens create recibosplit        # -> TURSO_AUTH_TOKEN
```

Put both values in a file named `.env` in the project root (never commit it — it's gitignored):

```
TURSO_DATABASE_URL=libsql://recibosplit-YOURNAME.turso.io
TURSO_AUTH_TOKEN=eyJhbGciOi...
```

### 3. Install backend dependencies

```bash
uv venv                                   # creates .venv
uv pip install -r requirements.txt
```

### 4. Install frontend dependencies

```bash
cd frontend && npm install && cd ..
```

### 5. (Optional) Load demo data

```bash
.venv/bin/python seed_test_data.py
```

Seeds three participants (Ana, Bruno, Carla) and two events with receipts, items, and assignments. Safe to re-run — it resets its own data and nothing else. Expected result in the Balances tab: Ana is owed $70, Bruno owes $55, Carla owes $15.

## Running the app

| What | Command | Where |
| --- | --- | --- |
| Backend API | `.venv/bin/uvicorn main:app --port 8000` | http://localhost:8000 (docs at `/docs`) |
| Frontend | `cd frontend && npm run dev` | http://localhost:5173 |
| Tests | `.venv/bin/python -m pytest tests/` | terminal (44 tests, fully offline) |

The flow in the UI: **Participants** (create people) → **Events** (create an event, add its participants, upload a receipt, capture items, assign each item) → **Balances** (per event and overall — black means owed, red means owes).

## Asking questions from Claude Code (MCP)

The project includes a read-only MCP server (`mcp_server.py`) already registered in `.mcp.json`. To use it:

1. Open Claude Code in this project folder and approve the `recibosplit` server when prompted (restart the session if it was already open).
2. Ask something like *"¿cuánto debe cada quien en total?"* or *"who owes what overall?"*.

It answers from live database data. Note: the **very first query after a fresh checkout takes about a minute** — it downloads a full local copy of the database (`recibosplit_mcp.db`). Every query after that is fast.

## Project structure

```
├── main.py             # FastAPI app — all HTTP endpoints
├── db.py               # All database access (connection, queries, sync)
├── services.py         # File storage + error mapping helpers
├── mcp_server.py       # Read-only MCP server for Claude Code
├── schema.sql          # Source of truth for tables and balance views
├── seed_test_data.py   # Demo data loader (idempotent)
├── tests/              # Offline pytest suite (temp DB per test)
├── frontend/           # React app (Vite)
├── migrations/         # Future schema changes (numbered)
├── CLAUDE.md           # Project context for Claude Code sessions
└── PROJECT_STATUS.md   # Build log, decisions, and Phase 1 checklist
```

Two design rules worth knowing before touching code:

- **Balance math lives ONLY in SQL** — the `event_balances` and `overall_balances` views in `schema.sql`. Python and React just read them.
- **One process per database file** — the local Turso replica (`recibosplit.db`) is exclusively locked. The MCP server avoids this by using its own replica file; scripts must not run while uvicorn is up (or must use `RECIBOSPLIT_DB_PATH` to pick another file).

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Locking error: Failed locking file` | Two processes on the same replica file | Stop uvicorn before running scripts, or set `RECIBOSPLIT_DB_PATH=other.db` |
| First MCP answer takes ~60 s | Initial full sync of a new replica | Wait once; it's fast afterwards |
| `near "ERT": syntax error` loading schema | pyturso `executescript()` bug with non-ASCII comments | Load the schema via `db.load_schema()`, never `executescript()` on `schema.sql` directly |
| App starts but hangs on first request | No network — Turso sync waits forever instead of failing | Check your connection and `.env` credentials |
| Browser console shows CORS errors | Frontend served from an unexpected origin | Use `npm run dev` (port 5173) — that origin is allowlisted in `main.py` |

## Out of scope (Phase 1)

- Automatic item/price recognition from the receipt photo (needs a vision model — planned as Phase 2).
- Debt simplification ("who pays whom directly" instead of net balances).

## How this was built

An educational project driven from Claude Code: a Fable 5 orchestrator session plans and reviews, while subagents in `.claude/agents/` (db-agent, api-agent, ui-agent, test-agent on Sonnet 5) write the code — one feature per day over a week. The full build log, day-by-day decisions, and the Phase 1 acceptance checklist live in [PROJECT_STATUS.md](PROJECT_STATUS.md).

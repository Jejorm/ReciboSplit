# CLAUDE.md

Persistent project context for Claude Code. Read this at the start of every session.

## What ReciboSplit is

A Splitwise-style app for splitting group expenses (cookouts, group trips). Phase 1: manual receipt image upload + manual item capture (no automatic vision-based recognition). Each item is assigned to one or more participants, and the app tracks who owes whom, cumulative across multiple events.

## Current status

Phase 1 is functionally **complete** — backend, frontend, tests (44 passed), and the MCP server are all built and verified. One inherited Phase 1 Definition-of-Done item still needs a human: a live chat test asking the `recibosplit` MCP server a balance question from inside Claude Code (don't lose this).

**Phase 2 is now active:** automatic receipt recognition via the **OpenAI vision API**. It is organized as Task 0–7 (not days) in `PROJECT_STATUS.md`. Phase 2 is strictly **additive** — it must not change any Phase 1 schema, view, endpoint behavior, or test. Extraction _pre-fills_ the existing manual capture form; it never replaces it, and manual capture stays fully usable if extraction is skipped or fails.

## Stack

- **Backend:** FastAPI (Python)
- **Database:** Turso (libSQL, SQLite-compatible) — **not Supabase, not plain SQLite**
- **Frontend:** React, local state (`useState`/`useReducer`), no external state libraries
- **Final packaging:** MCP server, so it can be queried from the Claude Code chat

## Decisions already made (don't reopen these without a reason)

- Python environment is managed with **uv**. Always use `uv pip install <package>` — never plain `pip install` — for any Python dependency, now or in future sessions (FastAPI, pytest, etc. included).
- Turso instead of Supabase or plain SQLite: same SQLite engine, but with remote access for multiple participants.
- No heavy ORM: explicit, parameterized SQL queries, both in `db-agent` and in any data-access code.
- Balance calculation lives in the SQL views `event_balances` and `overall_balances` in `schema.sql` — never duplicate that logic in Python or in the frontend.
- Automatic receipt recognition (vision/OCR) is **Phase 2**, now in progress — see the Task 0–7 plan in `PROJECT_STATUS.md`. It runs as a runtime call to the OpenAI vision API and must stay strictly additive to Phase 1.
- Vision model: **gpt-5.6-luna**, chosen for cost over accuracy during this early stage (verified real via direct OpenAI API call; ~2.5x cheaper than gpt-4o). Tested against gpt-4o, gpt-5.4-nano, and gpt-5.4-mini on 4 receipt conditions (clean/blurry/angled/dark+lowres) — luna was the only one that never invented a nonexistent line item, though it can still misread a price or drop a real item under bad photo conditions. Manual review before saving remains mandatory regardless of model. Revisit only if real-user testing shows too many extraction errors — don't reopen this choice without that evidence.
- **Two providers, two distinct roles** (do not mix them up): **Anthropic / Fable 5** is the _development_ orchestrator inside Claude Code (it writes and reviews the code). **OpenAI** is the _runtime_ vision engine the app calls to read receipt photos. The app never calls Anthropic at runtime, and Claude Code never uses OpenAI to build the project.

## How to work on this project

- The main session runs on **Fable 5** (`/model fable-5`) and acts as the orchestrator: plans, decides on design, reviews what the subagents deliver.
- Mechanical execution is delegated to subagents in `.claude/agents/`, all on **Sonnet 5**:
  - `db-agent` — Turso schema, migrations, queries
  - `api-agent` — FastAPI endpoints
  - `ui-agent` — React components
  - `test-agent` — pytest tests
  - `vision-agent` — Phase 2 only: OpenAI vision extractor, its JSON/Pydantic contract, the extraction endpoint, and the fallback path (never persists data, never opens its own Turso connection)
- Before writing new code, explicitly delegate to the right subagent instead of doing it directly in the main session.
- `schema.sql` is the source of truth for the schema. Any change is accompanied by a numbered migration in `/migrations`.

## At the start of every session

1. Read `PROJECT_STATUS.md` to see which Phase 2 task we're on and what's left.
2. Update `PROJECT_STATUS.md` at the end of the session with what was completed and the next step, and commit with a descriptive message (one commit per task, not one giant commit at the end).

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A personal bot that forwards **any plain text** a user types into Signal to a configurable HTTP target (a free [ntfy](https://ntfy.sh) topic by default), then replies in Signal with a `✅ sent (id …)` confirmation. Python + `signalbot`, packaged as two Docker services.

**Configurable target.** The destination is chosen at startup by `TargetBuilder.from_env().build()` (`src/targets/builder.py`) from `TARGET_URL` / `TARGET_TYPE` (default `ntfy`). The concrete client (`NtfyTarget`) implements the `Target` protocol in `src/targets/base.py` and self-registers in a name→factory registry, so a new endpoint type is a `register(...)` call, not a change to the bot wiring. `TARGET_URL` is the base endpoint; an optional `TARGET_TOPIC` is appended to it as a path segment (e.g. an ntfy topic).

## Commands

```bash
# Tests (need the dev venv once: python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt)
. .venv/bin/activate && pytest -q                       # all tests
pytest tests/test_forwarder.py::test_echo_guard_skips_own_reply   # single test

# Run the stack (see "First-run ordering" — linking must happen before the bot starts)
docker compose up -d signal-api                         # step 1: Signal API only
docker compose up -d bot                                # step 3: bot (after linking)
docker compose logs -f bot
```

Tests import modules from `src/` as top-level names — this works because `conftest.py` puts `src/` on `sys.path`, and `pytest.ini` sets `asyncio_mode = auto` (async tests need no decorator). Tests mock ntfy and the Signal context, so **no network or Signal service is required**.

## Architecture — the non-obvious parts

**Two processes, split by concern.** `signal-cli-rest-api` (Docker, `bbernhard/...`) owns the Signal protocol; our Python bot (`src/bot.py` via the `signalbot` library) is a thin dispatch layer. The bot receives over a WebSocket (`ws://signal-api:8080/v1/receive/{number}`) and sends over `POST /v2/send`. **`MODE=json-rpc` in `docker-compose.yml` is mandatory** — it is the only mode that exposes that receive WebSocket.

**The bot is a *linked device*, not a separate account.** It is linked to the user's own Signal account (like Signal Desktop) via QR — there is no bot phone number. Consequences that drive the design:
- The user talks to the bot through **Note to Self**. A Note-to-Self message arrives at a linked device as a `syncMessage.sentMessage`, **not** a normal `dataMessage`. `signalbot` maps this to `MessageType.SYNC_MESSAGE`, so `src/forward_command.py` forwards both `DATA_MESSAGE` and `SYNC_MESSAGE` (see `FORWARDABLE`).
- Because replies are sent from the *same* account, they can echo back as sync messages. The **echo-guard** in `ForwardCommand.handle` skips any incoming text starting with the reply prefix (`✅`) so the bot never forward-loops.

**Catch-all dispatch.** `ForwardCommand.handle` has **no `@triggered` decorator**, so `signalbot` runs it for *every* dispatched message — that is how "no message format required" is achieved. The handler must filter itself: it ignores non-text events (reactions, receipts, typing, contact-syncs are all dispatched too) and empty/whitespace text.

**Acceptance signal.** ntfy returns JSON with an `id` on a successful publish; that `id` is the proof the message was accepted and is surfaced in the Signal reply. For end-to-end verification, `GET https://ntfy.sh/<topic>/json?poll=1` returns the topic's recent messages.

## First-run ordering (important)

Linking must happen **before** the bot starts, because the bot's receive socket needs an already-linked account. Start `signal-api`, open `http://localhost:8080/v1/qrcodelink?device_name=signal-forwarder` and scan it in Signal (Settings → Linked devices), fill `.env`, then start `bot`. Full steps in `README.md`.

## Do not touch

`.env` (account number + ntfy token) and `signal-cli-config/` (the linked-device keys — effectively a Signal credential) are gitignored secrets. Never read, print, or commit them.

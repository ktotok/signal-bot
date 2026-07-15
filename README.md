# Signal → text forwarder

A tiny personal bot: type **any plain text** into Signal and it gets forwarded to
an HTTP endpoint you choose that you can watch from anywhere. No message format
required. The bot replies in Signal with a `✅ sent` confirmation so you know each
message was accepted.

The destination is **configurable**: point `TARGET_URL` at a free
[ntfy](https://ntfy.sh) topic (the built-in client). The client is selected from
config, and adding a new endpoint type is a one-line registration, not a change
to the bot — see [Adding a new target type](#adding-a-new-target-type).

```
Your phone (Signal · Note to Self)
        │  linked device (QR)
        ▼
signal-cli-rest-api  ──►  Python bot  ──►  TARGET_URL (ntfy)  ──►  ntfy app / web
        ▲                     │
        └──── "✅ sent" ◄──────┘
```

## How it works — the bot is a *linked device*

**The bot is a linked device on your own Signal account** — exactly like Signal
Desktop. It is **not** a separate contact and has **no phone number of its own**.
You link it from your phone by scanning a QR code (Signal → Settings → Linked
devices).

Because the bot *is* your account, you talk to it through **Note to Self** — the
private chat with yourself that every Signal account has (top of your chat list).
Anything you type there is forwarded to ntfy, and the bot replies in that same
chat. Note to Self is your private command line to the bot; no other person ever
sees these messages.

## ⚠️ Security warnings — read before running

- **A linked device can see your account's message traffic.** Like Signal Desktop,
  this bot receives your account's messages; the code only *acts on* Note-to-Self
  text, but the data passes through whatever host runs the containers.
  **Only run it on a machine you fully trust and control.**
- **Guard the `signal-cli-config/` directory.** It holds the linked-device keys —
  effectively a credential to your Signal account. Keep it private, never commit
  it, restrict its permissions, and back it up securely. Deleting it de-links the
  bot (you'd re-link with a new QR).
- **Never commit `.env`.** It contains your phone number, target URL, and any
  `TARGET_TOKEN`. It's in `.gitignore` — keep it there.
- **Public ntfy topics are readable by anyone who guesses the name.** Use a long,
  random topic (e.g. `signal-fwd-9f3a7c21b8`); for anything sensitive, set
  `TARGET_TOKEN` with a reserved or self-hosted endpoint instead of a public one.
- **Forwarded text leaves Signal's encryption.** The moment the bot forwards a
  message it travels to and is cached by the target server in the clear (per that
  server's policy). Don't forward secrets you wouldn't post there.
- **Revoking access:** unlink anytime from Signal → Settings → Linked devices →
  remove the `signal-forwarder` device; then stop the containers and delete
  `signal-cli-config/`.

## Setup

Requirements: Docker + Docker Compose. First run is **two steps** — you must link
the device *before* starting the bot, because the bot's receive socket needs an
already-linked account.

### 1. Start the Signal API and link your phone

```bash
docker compose up -d signal-api

# wait until ready (prints 204):
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/v1/health
# confirm json-rpc mode:
curl -s http://localhost:8080/v1/about
```

Open the QR link in a browser:

```
http://localhost:8080/v1/qrcodelink?device_name=signal-forwarder
```

On your phone: **Signal → Settings → Linked devices → +  (Link new device) →
scan the QR.** Wait ~10–30 s for the initial sync. Note your Signal account
number in E.164 form (e.g. `+15551234567`).

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:

- `PHONE_NUMBER` — your Signal account number (`+…`).
- `TARGET_URL` — where to forward, e.g. `https://ntfy.sh/<your-random-topic>`
  (or a base URL like `https://ntfy.sh` plus `TARGET_TOPIC`).
- optional: `TARGET_TYPE`, `TARGET_TOPIC`, `TARGET_TOKEN`, `REPLY_ON_SUCCESS`.

Subscribe to the topic so you can watch messages arrive: install the ntfy app
(iOS/Android) and add your topic, or open `https://ntfy.sh/<your-topic>` in a
browser.

### 3. Start the bot

```bash
docker compose up -d bot
docker compose logs -f bot
```

If you change the bot's code (`src/`, `Dockerfile`, `requirements*.txt`), rebuild
the image before restarting so the container picks up the change:

```bash
docker compose up -d --build bot
```

## Usage

Open **Note to Self** in Signal and send any text. It appears at your target
within a second, and the bot replies `✅ sent (id …)`.

## Testing

Unit tests run without any Signal service or network (they mock the target and
the Signal context):

```bash
pip install -r requirements-dev.txt
pytest -q
```

Automated end-to-end check that a message was **accepted** — publish, then poll
the topic's recent messages and confirm your text is there:

```bash
curl -s "https://ntfy.sh/<your-topic>/json?poll=1"
```

## Configuration reference

| Variable           | Required | Default            | Description                                            |
| ------------------ | -------- | ------------------ | ------------------------------------------------------ |
| `PHONE_NUMBER`     | yes      | —                  | Linked Signal account number, E.164 (`+…`).            |
| `TARGET_URL`       | yes      | —                  | Endpoint URL. Full URL, or a base to combine with `TARGET_TOPIC`. |
| `TARGET_TYPE`      | no       | `ntfy`             | Client to use. `ntfy` is built in; others via `register()`. |
| `TARGET_TOPIC`     | no       | —                  | Path segment appended to `TARGET_URL` (e.g. an ntfy topic). |
| `TARGET_TOKEN`     | no       | —                  | Bearer token sent as `Authorization` header.           |
| `REPLY_ON_SUCCESS` | no       | `true`             | Reply in Signal after each forward.                    |
| `SIGNAL_SERVICE`   | no*      | `signal-api:8080`  | signal-cli-rest-api address (set by compose).          |

\* Required only outside docker-compose.

### Adding a new target type

Implement a client with an `async def publish(self, text) -> dict` method (see
`src/targets/base.py`), then register it:

```python
from targets import register
register("mytype", lambda url, token: MyClient(url, token=token))
```

Set `TARGET_TYPE=mytype` and it's selected at startup — no other code changes.

## Project layout

```
.
├── docker-compose.yml     # signal-api (json-rpc) + bot
├── Dockerfile             # python bot image
├── requirements*.txt      # runtime / dev deps
├── .env.example           # copy to .env
├── src/
│   ├── targets/           # pluggable publish clients
│   │   ├── base.py        #   Target protocol (the contract)
│   │   ├── ntfy.py        #   ntfy client (built in)
│   │   └── builder.py     #   TargetBuilder + registry (config → client)
│   ├── forward_command.py # catch-all: forward text + confirm
│   └── bot.py             # wiring + start
└── tests/
    ├── test_forwarder.py  # ForwardCommand behavior
    └── test_targets.py    # builder / client selection
```

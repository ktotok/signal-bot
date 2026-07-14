# Signal → ntfy text forwarder

A tiny personal bot: type **any plain text** into Signal and it gets forwarded to
a free [ntfy](https://ntfy.sh) topic that you can watch from anywhere. No message
format required. The bot replies in Signal with a `✅ sent` confirmation so you
know each message was accepted.

```
Your phone (Signal · Note to Self)
        │  linked device (QR)
        ▼
signal-cli-rest-api  ──►  Python bot  ──►  https://ntfy.sh/<your-topic>  ──►  ntfy app / web
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
- **Never commit `.env`.** It contains your phone number, ntfy topic, and any
  `NTFY_TOKEN`. It's in `.gitignore` — keep it there.
- **Public ntfy topics are readable by anyone who guesses the name.** Use a long,
  random topic (e.g. `signal-fwd-9f3a7c21b8`); for anything sensitive, set
  `NTFY_TOKEN` with a reserved or self-hosted topic instead of public `ntfy.sh`.
- **Forwarded text leaves Signal's encryption.** The moment the bot forwards a
  message to ntfy it travels to and is cached by the ntfy server in the clear
  (per that server's policy). Don't forward secrets you wouldn't post there.
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
- `NTFY_TOPIC` — a long, random topic name.
- optional: `NTFY_SERVER`, `NTFY_TOKEN`, `REPLY_ON_SUCCESS`.

Subscribe to the topic so you can watch messages arrive: install the ntfy app
(iOS/Android) and add your topic, or open `https://ntfy.sh/<your-topic>` in a
browser.

### 3. Start the bot

```bash
docker compose up -d bot
docker compose logs -f bot
```

## Usage

Open **Note to Self** in Signal and send any text. It appears on your ntfy topic
within a second, and the bot replies `✅ sent to ntfy (id …)`.

## Testing

Unit tests run without any Signal service or network (they mock ntfy and the
Signal context):

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
| `NTFY_TOPIC`       | yes      | —                  | ntfy topic to publish to. Use a random name.           |
| `NTFY_SERVER`      | no       | `https://ntfy.sh`  | ntfy server base URL.                                  |
| `NTFY_TOKEN`       | no       | —                  | Bearer token for a reserved/self-hosted topic.         |
| `REPLY_ON_SUCCESS` | no       | `true`             | Reply in Signal after each forward.                    |
| `SIGNAL_SERVICE`   | no*      | `signal-api:8080`  | signal-cli-rest-api address (set by compose).          |

\* Required only outside docker-compose.

## Project layout

```
.
├── docker-compose.yml     # signal-api (json-rpc) + bot
├── Dockerfile             # python bot image
├── requirements*.txt      # runtime / dev deps
├── .env.example           # copy to .env
├── src/
│   ├── ntfy_client.py     # async POST to ntfy
│   ├── forward_command.py # catch-all: forward text + confirm
│   └── bot.py             # wiring + start
└── tests/test_forwarder.py
```

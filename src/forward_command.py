"""Catch-all Signal command that forwards any text message to ntfy.

The command has no ``@triggered`` decorator, so signalbot runs ``handle`` for
*every* dispatched message. We forward the text of normal messages and of
Note-to-Self / linked-device messages, then reply in Signal with a status line.
"""

from __future__ import annotations

import logging

from signalbot import Command, Context
from signalbot.message import MessageType

log = logging.getLogger(__name__)

# Only these carry user-typed text. Reactions, receipts, typing indicators and
# contact-syncs are dispatched too, but must not be forwarded.
FORWARDABLE = {MessageType.DATA_MESSAGE, MessageType.SYNC_MESSAGE}


class ForwardCommand(Command):
    def __init__(
        self,
        ntfy,
        reply_on_success: bool = True,
        reply_prefix: str = "✅",
    ):
        super().__init__()
        self._ntfy = ntfy
        self._reply = reply_on_success
        self._prefix = reply_prefix

    async def handle(self, c: Context) -> None:
        m = c.message

        if m.type not in FORWARDABLE:
            return

        text = (m.text or "").strip()
        if not text:
            return

        # Echo-guard: our own confirmation replies are sent from the same
        # account and can come back as sync messages. Skip anything that looks
        # like one of our replies so we never forward-loop.
        if text.startswith(self._prefix):
            return

        try:
            result = await self._ntfy.publish(text)
            status = f"{self._prefix} sent to ntfy (id {result.get('id', '?')})"
        except Exception as e:  # noqa: BLE001 — report any failure to the user
            log.exception("ntfy publish failed")
            status = f"⚠️ failed to send: {e}"

        log.info("forwarded %d chars -> %s", len(text), status)

        if self._reply:
            await c.send(status)

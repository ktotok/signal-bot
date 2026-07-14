"""Thin async client for publishing plain text to an ntfy topic.

ntfy (https://ntfy.sh) treats the raw request body as the notification
message, so we POST the text as-is. On success ntfy responds with a JSON
object describing the published message, including its ``id`` — which we use
as proof that the message was accepted.
"""

from __future__ import annotations

import httpx


class NtfyClient:
    def __init__(self, server: str, topic: str, token: str | None = None):
        self._url = f"{server.rstrip('/')}/{topic}"
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}

    async def publish(self, text: str) -> dict:
        """Publish ``text`` to the topic. Returns ntfy's JSON response.

        Raises ``httpx.HTTPStatusError`` for non-2xx responses so callers can
        report failure back to the user.
        """
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                self._url,
                content=text.encode("utf-8"),
                headers=self._headers,
            )
            resp.raise_for_status()
            try:
                return resp.json()  # {"id": "...", "time": ..., "topic": "..."}
            except ValueError:
                # Non-ntfy endpoint that doesn't return JSON — still a success.
                return {"id": "?"}

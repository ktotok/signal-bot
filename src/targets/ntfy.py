"""Target that publishes to an ntfy topic.

ntfy (https://ntfy.sh) treats the raw request body as the notification
message, so we POST the text as-is. On success ntfy responds with a JSON
object describing the published message, including its ``id`` — which we use
as proof that the message was accepted.
"""

from __future__ import annotations

import httpx


class NtfyTarget:
    """POST raw text to an ntfy topic URL (e.g. ``https://ntfy.sh/mytopic``)."""

    def __init__(self, url: str, token: str | None = None, timeout: float = 10):
        self._url = url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._timeout = timeout

    async def publish(self, text: str) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                self._url,
                content=text.encode("utf-8"),
                headers=self._headers,
            )
            resp.raise_for_status()
            try:
                return resp.json()  # {"id": "...", "time": ..., "topic": "..."}
            except ValueError:
                # Endpoint accepted us but returned no JSON — still a success.
                return {"id": "?"}

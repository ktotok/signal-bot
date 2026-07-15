"""The publish target contract every client implements.

A *target* is anything the bot can hand a piece of text to. The bot only ever
depends on this ``Target`` protocol, never on a concrete client, so swapping
ntfy for another endpoint is a config change, not a code change. New client
types satisfy the same protocol and register themselves with the builder (see
``targets.builder``).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Target(Protocol):
    async def publish(self, text: str) -> dict:
        """Send ``text`` to the endpoint.

        Returns a dict describing the accepted message. It must contain an
        ``id`` key (proof of acceptance, surfaced in the Signal reply); clients
        that talk to endpoints without a natural id should synthesize one.

        Should raise on a non-2xx / transport failure so the caller can report
        it back to the user.
        """
        ...

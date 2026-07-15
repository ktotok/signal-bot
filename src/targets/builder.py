"""Assemble a ``Target`` from configuration — the one place wiring lives.

``TargetBuilder`` is a small fluent builder. It holds a *registry* mapping a
kind name (``"ntfy"``, …) to a factory, so adding support for a new endpoint is
a one-line ``register()`` call, not an edit to the bot or this builder.
``from_env`` reads the process environment into a builder; ``build`` resolves
the kind (explicit ``TARGET_TYPE``, else the ``ntfy`` default) and calls its
factory.

Environment variables (see ``.env.example``):
    TARGET_URL   base endpoint URL, e.g. https://ntfy.sh (required)
    TARGET_TYPE  client to use (optional; defaults to "ntfy")
    TARGET_TOKEN bearer token (optional)
    TARGET_TOPIC path segment appended to TARGET_URL (optional; e.g. an ntfy
                 topic). When unset, TARGET_URL is used as-is.
"""

from __future__ import annotations

import os
from typing import Callable, Mapping

from .base import Target
from .ntfy import NtfyTarget

# A factory takes the resolved config and returns a Target.
Factory = Callable[..., Target]

DEFAULT_KIND = "ntfy"

_REGISTRY: dict[str, Factory] = {}


def register(kind: str, factory: Factory) -> None:
    """Register a target ``kind`` so the builder can construct it by name."""
    _REGISTRY[kind] = factory


def registered_kinds() -> list[str]:
    return sorted(_REGISTRY)


register("ntfy", lambda url, token: NtfyTarget(url, token=token))


class TargetBuilder:
    def __init__(self) -> None:
        self._url: str | None = None
        self._kind: str | None = None
        self._token: str | None = None
        self._topic: str | None = None

    def url(self, url: str | None) -> "TargetBuilder":
        self._url = url
        return self

    def kind(self, kind: str | None) -> "TargetBuilder":
        self._kind = kind
        return self

    def token(self, token: str | None) -> "TargetBuilder":
        self._token = token
        return self

    def topic(self, topic: str | None) -> "TargetBuilder":
        self._topic = topic
        return self

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "TargetBuilder":
        env = os.environ if env is None else env
        return (
            cls()
            .url(env.get("TARGET_URL"))
            .kind(env.get("TARGET_TYPE"))
            .token(env.get("TARGET_TOKEN"))
            .topic(env.get("TARGET_TOPIC"))
        )

    def build(self) -> Target:
        if not self._url:
            raise ValueError(
                "no target URL configured — set TARGET_URL in the environment"
            )
        # A topic (e.g. an ntfy topic) is an optional path segment appended to
        # the base URL. Strip slashes on both sides so a trailing slash on the
        # base or a leading slash on the topic can't produce a "//".
        url = self._url
        if self._topic:
            url = f"{url.rstrip('/')}/{self._topic.strip('/')}"

        kind = self._kind or DEFAULT_KIND
        try:
            factory = _REGISTRY[kind]
        except KeyError:
            raise ValueError(
                f"unknown target type {kind!r}; registered: {registered_kinds()}"
            ) from None
        return factory(url=url, token=self._token)

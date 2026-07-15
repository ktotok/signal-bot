"""Pluggable publish targets and the builder that assembles them.

    from targets import TargetBuilder
    target = TargetBuilder.from_env().build()

The bot depends only on the ``Target`` protocol; the concrete client is selected
at runtime by ``TargetBuilder`` from configuration. ntfy ships built in; other
endpoints are added with ``register()`` (see ``targets.builder``).
"""

from .base import Target
from .builder import TargetBuilder, register, registered_kinds
from .ntfy import NtfyTarget

__all__ = [
    "Target",
    "TargetBuilder",
    "NtfyTarget",
    "register",
    "registered_kinds",
]

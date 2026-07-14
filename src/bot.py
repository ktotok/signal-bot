"""Entry point: wire config, register the forwarder, and start the bot.

Run with ``python src/bot.py`` (that is what the Docker image does). Requires
the signal-cli-rest-api service to be reachable and the account already linked.
"""

from __future__ import annotations

import logging
import os

from signalbot import Config, SignalBot, enable_console_logging

from forward_command import ForwardCommand
from targets import TargetBuilder


def main() -> None:
    enable_console_logging(logging.INFO)

    target = TargetBuilder.from_env().build()

    bot = SignalBot(
        Config(
            signal_service=os.environ["SIGNAL_SERVICE"],  # e.g. signal-api:8080
            phone_number=os.environ["PHONE_NUMBER"],      # your linked account, +country…
        )
    )

    reply = os.environ.get("REPLY_ON_SUCCESS", "true").lower() == "true"
    bot.register(
        ForwardCommand(target, reply_on_success=reply),
        contacts=True,
        groups=True,
    )

    logging.getLogger(__name__).info("Signal → target forwarder starting")
    bot.start()


if __name__ == "__main__":
    main()

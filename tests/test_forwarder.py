"""Unit tests for ForwardCommand.

We drive ``handle`` directly with a fake Context and a fake ntfy client, so no
Signal service or network is needed. asyncio_mode=auto (pytest.ini) lets the
async test functions run without decorators.
"""

from types import SimpleNamespace

from signalbot.message import MessageType

from forward_command import ForwardCommand


class FakeNtfy:
    def __init__(self, result=None, exc=None):
        self.result = result if result is not None else {"id": "abc123"}
        self.exc = exc
        self.calls = []

    async def publish(self, text):
        self.calls.append(text)
        if self.exc:
            raise self.exc
        return self.result


class FakeContext:
    def __init__(self, text, mtype=MessageType.SYNC_MESSAGE, ts=1):
        self.message = SimpleNamespace(text=text, type=mtype, timestamp=ts)
        self.sent = []

    async def send(self, text):
        self.sent.append(text)


async def test_forwards_note_to_self_and_confirms():
    ntfy = FakeNtfy()
    cmd = ForwardCommand(ntfy)
    ctx = FakeContext("buy milk")

    await cmd.handle(ctx)

    assert ntfy.calls == ["buy milk"]
    assert ctx.sent and ctx.sent[0].startswith("✅")
    assert "abc123" in ctx.sent[0]


async def test_forwards_normal_data_message():
    ntfy = FakeNtfy()
    cmd = ForwardCommand(ntfy)
    ctx = FakeContext("hello", mtype=MessageType.DATA_MESSAGE)

    await cmd.handle(ctx)

    assert ntfy.calls == ["hello"]


async def test_ntfy_failure_reports_and_does_not_raise():
    ntfy = FakeNtfy(exc=RuntimeError("boom"))
    cmd = ForwardCommand(ntfy)
    ctx = FakeContext("something")

    await cmd.handle(ctx)  # must not raise

    assert ntfy.calls == ["something"]
    assert ctx.sent and ctx.sent[0].startswith("⚠️")


async def test_ignores_empty_and_whitespace():
    ntfy = FakeNtfy()
    cmd = ForwardCommand(ntfy)

    await cmd.handle(FakeContext(""))
    await cmd.handle(FakeContext("   "))
    await cmd.handle(FakeContext(None))

    assert ntfy.calls == []


async def test_ignores_non_text_message_types():
    ntfy = FakeNtfy()
    cmd = ForwardCommand(ntfy)

    await cmd.handle(FakeContext("x", mtype=MessageType.REACTION_MESSAGE))
    await cmd.handle(FakeContext("y", mtype=MessageType.READ_MESSAGE))

    assert ntfy.calls == []


async def test_echo_guard_skips_own_reply():
    ntfy = FakeNtfy()
    cmd = ForwardCommand(ntfy)
    ctx = FakeContext("✅ sent to ntfy (id abc123)")

    await cmd.handle(ctx)

    assert ntfy.calls == []  # our own confirmation must not be re-forwarded
    assert ctx.sent == []


async def test_reply_disabled():
    ntfy = FakeNtfy()
    cmd = ForwardCommand(ntfy, reply_on_success=False)
    ctx = FakeContext("silent")

    await cmd.handle(ctx)

    assert ntfy.calls == ["silent"]
    assert ctx.sent == []  # no confirmation sent when replies are off

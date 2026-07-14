"""Unit tests for the target builder and its client selection.

No network is used: we only assert which client the builder produces and how it
was configured from environment variables.
"""

import pytest

from targets import NtfyTarget, TargetBuilder, register, registered_kinds


def test_builds_ntfy_from_target_url():
    t = TargetBuilder.from_env({"TARGET_URL": "https://ntfy.sh/my-topic"}).build()
    assert isinstance(t, NtfyTarget)
    assert t._url == "https://ntfy.sh/my-topic"


def test_defaults_to_ntfy_when_type_omitted():
    t = TargetBuilder.from_env({"TARGET_URL": "https://example.com/topic"}).build()
    assert isinstance(t, NtfyTarget)


def test_token_is_applied():
    t = TargetBuilder.from_env(
        {"TARGET_URL": "https://ntfy.sh/t", "TARGET_TOKEN": "secret"}
    ).build()
    assert t._headers == {"Authorization": "Bearer secret"}


def test_legacy_ntfy_env_still_works():
    t = TargetBuilder.from_env(
        {"NTFY_TOPIC": "legacy-topic", "NTFY_TOKEN": "tk_1"}
    ).build()
    assert isinstance(t, NtfyTarget)
    assert t._url == "https://ntfy.sh/legacy-topic"
    assert t._headers == {"Authorization": "Bearer tk_1"}


def test_legacy_ntfy_custom_server():
    t = TargetBuilder.from_env(
        {"NTFY_TOPIC": "t", "NTFY_SERVER": "https://ntfy.example.com/"}
    ).build()
    assert t._url == "https://ntfy.example.com/t"


def test_missing_url_raises():
    with pytest.raises(ValueError, match="no target URL"):
        TargetBuilder.from_env({}).build()


def test_unknown_type_raises():
    with pytest.raises(ValueError, match="unknown target type"):
        TargetBuilder.from_env(
            {"TARGET_URL": "https://x.com", "TARGET_TYPE": "carrier-pigeon"}
        ).build()


def test_fluent_api():
    t = TargetBuilder().url("https://ntfy.sh/h").token("z").build()
    assert isinstance(t, NtfyTarget)
    assert t._headers == {"Authorization": "Bearer z"}


def test_register_new_kind_is_pluggable():
    class Dummy:
        def __init__(self, url, token=None):
            self.url = url

        async def publish(self, text):
            return {"id": "dummy"}

    register("dummy", lambda url, token: Dummy(url))
    assert "dummy" in registered_kinds()

    t = TargetBuilder().url("proto://x").kind("dummy").build()
    assert isinstance(t, Dummy)

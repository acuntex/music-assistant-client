"""Tests for announcement playback."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from music_assistant_client.constants import (
    ANNOUNCEMENT_MODE_DEVICE,
    ANNOUNCEMENT_MODE_OVERLAY,
    ANNOUNCEMENT_OVERLAY_SCHEMA_VERSION,
)
from music_assistant_client.players import Players


@pytest.fixture
def send_command() -> AsyncMock:
    """Capture API payloads without sending commands."""
    return AsyncMock(return_value=None)


@pytest.fixture
def players(send_command: AsyncMock) -> Players:
    """Provide player wrappers backed by the captured command transport."""
    client = SimpleNamespace(subscribe=lambda *_args, **_kwargs: None, send_command=send_command)
    return Players(client)  # type: ignore[arg-type]


def sent(send_command: AsyncMock) -> tuple[str, dict[str, Any]]:
    """Return the command and keyword arguments the client would send."""
    args, kwargs = send_command.call_args
    return args[0], kwargs


async def test_announcement_defaults_to_interrupting_playback(
    players: Players, send_command: AsyncMock
) -> None:
    """Without a mode an announcement behaves as it always did, on every server."""
    await players.play_announcement("player_1", url="http://example.com/clip.mp3")

    command, kwargs = sent(send_command)
    assert command == "players/cmd/play_announcement"
    assert kwargs["mode"] == ANNOUNCEMENT_MODE_DEVICE
    assert kwargs["require_schema"] is None


async def test_overlay_announcement_needs_a_server_that_has_it(
    players: Players, send_command: AsyncMock
) -> None:
    """Mixing into the stream is refused up front by a server without the bus."""
    await players.play_announcement(
        "player_1", url="http://example.com/clip.mp3", mode=ANNOUNCEMENT_MODE_OVERLAY
    )

    _, kwargs = sent(send_command)
    assert kwargs["mode"] == ANNOUNCEMENT_MODE_OVERLAY
    assert kwargs["require_schema"] == ANNOUNCEMENT_OVERLAY_SCHEMA_VERSION


async def test_overlay_keeps_its_gate_when_lower_arguments_need_one(
    players: Players, send_command: AsyncMock
) -> None:
    """A message with a language asks for schema 47, the overlay for more than that."""
    await players.play_announcement(
        "player_1", message="Dinner is ready", language="en-US", mode=ANNOUNCEMENT_MODE_OVERLAY
    )

    _, kwargs = sent(send_command)
    assert kwargs["require_schema"] == ANNOUNCEMENT_OVERLAY_SCHEMA_VERSION


async def test_language_alone_keeps_its_own_gate(players: Players, send_command: AsyncMock) -> None:
    """Speaking a message in a language still only asks for the schema it needs."""
    await players.play_announcement("player_1", message="Dinner is ready", language="en-US")

    _, kwargs = sent(send_command)
    assert kwargs["require_schema"] == 47

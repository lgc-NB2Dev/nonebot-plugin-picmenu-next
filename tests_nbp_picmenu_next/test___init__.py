"""Tests for package initialization."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


async def test_startup_refreshes_plugin_information(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """The registered startup hook refreshes PicMenu's plugin information once."""
    import nonebot_plugin_picmenu_next as plugin

    calls: list[str] = []

    async def refresh() -> list[object]:
        calls.append("refresh")
        return []

    monkeypatch.setattr(plugin, "refresh_infos", refresh)

    await plugin._()

    assert calls == ["refresh"]

"""Tests for the help-data registry module."""

from types import SimpleNamespace
from typing import TYPE_CHECKING

from nonebot.plugin import PluginMetadata

if TYPE_CHECKING:
    import pytest


async def test_refresh_infos_sorts_and_publishes_the_current_snapshot(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """Refreshing records the pinyin-sorted snapshot returned to command rendering."""
    from nonebot_plugin_picmenu_next import data_source
    from nonebot_plugin_picmenu_next.data_source import collect

    metadata = PluginMetadata(
        name="同名插件",
        description="description",
        usage="usage",
        extra={},
    )
    plugins = [
        SimpleNamespace(id_="z_plugin", module_name="z_plugin", metadata=metadata),
        SimpleNamespace(id_="a_plugin", module_name="a_plugin", metadata=metadata),
    ]
    monkeypatch.setattr(data_source, "_get_loaded_plugins", lambda: plugins)
    monkeypatch.setattr(collect, "collect_menus", dict)

    refreshed = await data_source.refresh_infos()

    assert [info.plugin_id for info in refreshed] == ["a_plugin", "z_plugin"]
    assert data_source.get_infos() is refreshed

"""Tests for the command entry module."""

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

from arclet.alconna import Alconna, CommandMeta, command_manager
from nonebot.adapters import Bot, Event

if TYPE_CHECKING:
    import pytest


def teardown_function() -> None:
    for command in command_manager.get_commands():
        if "-picmenu" in command.path:
            command_manager.delete(command)


def _owned_command(name: str, plugin_id: str) -> Alconna:
    command = Alconna(name, meta=CommandMeta(description=f"{name} description"))
    command.meta.extra["matcher.source"] = SimpleNamespace(plugin_id=plugin_id)
    return command


async def _inject_context(_dependent: object) -> Bot:
    return cast("Bot", SimpleNamespace(adapter=SimpleNamespace()))


async def test_render_menu_uses_function_template_before_plugin_inheritance(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0014 gives a function template precedence over inherited plugin choice."""
    from nonebot_plugin_alconna.uniseg import UniMessage
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import (
        PMDataItem,
        PMNData,
        PMNPluginInfo,
    )

    async def unchanged_main(infos: list[PMNPluginInfo]) -> list[PMNPluginInfo]:
        return infos

    async def unchanged_detail(info: PMNPluginInfo) -> PMNPluginInfo:
        return info

    async def inherited(*_args: object, **_kwargs: object) -> UniMessage:
        return UniMessage("inherited")

    async def item(*_args: object, **_kwargs: object) -> UniMessage:
        return UniMessage("item")

    info = PMNPluginInfo(
        name="templates",
        pmn=PMNData(template="inherited"),
        pm_data=[
            PMDataItem(
                func="item",
                trigger_method="item",
                trigger_condition="command",
                brief_des="item",
                detail_des="item",
                pmn_template="item",
            )
        ],
    )
    monkeypatch.setattr(main, "get_infos", lambda: [info])
    monkeypatch.setattr(main, "resolve_main_mixin", unchanged_main)
    monkeypatch.setattr(main, "resolve_detail_mixin", unchanged_detail)
    monkeypatch.setitem(main.func_detail_templates.data, "inherited", inherited)
    monkeypatch.setitem(main.func_detail_templates.data, "item", item)

    msg, _, _ = await main.render_menu(
        cast("Bot", SimpleNamespace(adapter=SimpleNamespace())),
        cast("Event", SimpleNamespace()),
        q_plugin="1",
        q_function="1",
    )

    assert msg is not None
    assert msg.extract_plain_text() == "item"


async def test_render_menu_generates_current_alconna_item_after_hidden_retry(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0013 creates a temporary item for an invoked command missing from data."""
    from nonebot_plugin_alconna.uniseg import UniMessage
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMDataItem, PMNPluginInfo

    command = _owned_command("temporary-picmenu", "temporary_plugin")
    captured: dict[str, object] = {}

    async def unchanged_main(infos: list[PMNPluginInfo]) -> list[PMNPluginInfo]:
        return infos

    async def unchanged_detail(info: PMNPluginInfo) -> PMNPluginInfo:
        return info

    async def render_temporary(
        _info: PMNPluginInfo,
        _info_index: int,
        func: PMDataItem,
        func_index: int | None,
        _showing_hidden: bool,
        _user_can_see_hidden: bool | None,
    ) -> UniMessage:
        captured.update(func=func, func_index=func_index)
        return UniMessage("temporary")

    info = PMNPluginInfo(name="temporary", plugin_id="temporary_plugin", pm_data=[])
    monkeypatch.setattr(main, "get_infos", lambda: [info])
    monkeypatch.setattr(main, "resolve_main_mixin", unchanged_main)
    monkeypatch.setattr(main, "resolve_detail_mixin", unchanged_detail)
    monkeypatch.setitem(main.func_detail_templates.data, "default", render_temporary)

    msg, rendered_info, rendered_func = await main.render_menu(
        cast("Bot", SimpleNamespace(adapter=SimpleNamespace())),
        cast("Event", SimpleNamespace()),
        plugin_id="temporary_plugin",
        alc_cmd_id=command.path,
        alc_command=command,
        alc_detail_des="current help",
        show_hidden=True,
    )

    assert msg is not None
    assert msg.extract_plain_text() == "temporary"
    assert rendered_info is info
    assert rendered_func is captured["func"]
    assert captured["func_index"] is None
    assert rendered_func is not None
    assert rendered_func.detail_des == "current help"


async def test_render_menu_returns_plugin_when_requested_function_data_is_absent(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """A normal function query preserves the matched plugin when it has no functions."""
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    async def unchanged(infos: list[PMNPluginInfo]) -> list[PMNPluginInfo]:
        return infos

    async def unchanged_detail(info: PMNPluginInfo) -> PMNPluginInfo:
        return info

    info = PMNPluginInfo(name="empty", plugin_id="empty", pm_data=None)
    monkeypatch.setattr(main, "get_infos", lambda: [info])
    monkeypatch.setattr(main, "resolve_main_mixin", unchanged)
    monkeypatch.setattr(main, "resolve_detail_mixin", unchanged_detail)

    assert await main.render_menu(
        cast("Bot", SimpleNamespace(adapter=SimpleNamespace())),
        cast("Event", SimpleNamespace()),
        q_plugin="1",
        q_function="1",
    ) == (None, info, None)


async def test_render_menu_covers_unmatched_plugin_detail_and_function_queries(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """Menu rendering preserves the matched plugin across query and detail outcomes."""
    from nonebot_plugin_alconna.uniseg import UniMessage
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMDataItem, PMNPluginInfo

    async def unchanged_main(infos: list[PMNPluginInfo]) -> list[PMNPluginInfo]:
        return infos

    async def unchanged_detail(info: PMNPluginInfo) -> PMNPluginInfo:
        return info

    async def detail_template(*_args: object, **_kwargs: object) -> UniMessage:
        return UniMessage("detail")

    async def no_matching_plugin(*_args: object) -> None:
        return None

    async def no_matching_function(*_args: object) -> None:
        return None

    item = PMDataItem(
        func="function",
        trigger_method="function",
        trigger_condition="command",
        brief_des="brief",
        detail_des="detail",
    )
    info = PMNPluginInfo(name="plugin", plugin_id="plugin", pm_data=[item])
    monkeypatch.setattr(main, "get_infos", lambda: [info])
    monkeypatch.setattr(main, "resolve_main_mixin", unchanged_main)
    monkeypatch.setattr(main, "resolve_detail_mixin", unchanged_detail)
    monkeypatch.setitem(main.detail_templates.data, "default", detail_template)
    monkeypatch.setattr(main, "query_plugin", no_matching_plugin)

    bot = cast("Bot", SimpleNamespace(adapter=SimpleNamespace()))
    event = cast("Event", SimpleNamespace())
    assert await main.render_menu(
        bot,
        event,
        q_plugin="missing",
    ) == (None, None, None)

    detail, detail_info, detail_func = await main.render_menu(
        bot,
        event,
        plugin_id="plugin",
    )
    assert detail is not None
    assert detail.extract_plain_text() == "detail"
    assert detail_info is not None
    assert detail_info.plugin_id == "plugin"
    assert detail_func is None

    monkeypatch.setattr(main, "query_func_detail", no_matching_function)
    missing, missing_info, missing_func = await cast("Any", main.render_menu)(
        bot,
        event,
        plugin_id="plugin",
        q_function="missing",
    )
    assert missing is None
    assert missing_info is not None
    assert missing_info.plugin_id == "plugin"
    assert missing_func is None

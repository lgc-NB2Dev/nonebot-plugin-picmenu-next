"""Tests for the command entry module."""

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from arclet.alconna import Alconna, CommandMeta, command_manager
from nonebot.adapters import Bot

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


async def test_help_interception_uses_visible_result_without_hidden_retry(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0013 keeps normal hidden filtering when the first render succeeds."""
    from nonebot_plugin_alconna.uniseg import UniMessage
    from nonebot_plugin_picmenu_next import __main__ as main

    command = _owned_command("visible-picmenu", "visible_plugin")
    ext = main.PMNHelpExtension()
    ext.command = command
    calls: list[dict[str, object]] = []

    async def render_visible(*_args: object, **kwargs: object) -> object:
        calls.append(dict(kwargs))
        return UniMessage("visible result"), None, None

    monkeypatch.setattr(ext, "inject", _inject_context)
    monkeypatch.setattr(main, "render_menu", render_visible)

    msg = await ext.output_converter("help", "Alconna fallback")

    assert msg.extract_plain_text() == "visible result"
    assert [call["show_hidden"] for call in calls] == [False]
    assert calls[0]["alc_cmd_id"] == command.path


async def test_help_interception_retries_hidden_items_only_after_no_result(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0013 retries once with hidden filtering relaxed after a normal miss."""
    from nonebot_plugin_alconna.uniseg import UniMessage
    from nonebot_plugin_picmenu_next import __main__ as main

    command = _owned_command("hidden-picmenu", "hidden_plugin")
    ext = main.PMNHelpExtension()
    ext.command = command
    calls: list[dict[str, object]] = []

    async def render_after_hidden_retry(*_args: object, **kwargs: object) -> object:
        calls.append(dict(kwargs))
        if kwargs["show_hidden"]:
            return UniMessage("hidden result"), None, None
        return None, None, None

    monkeypatch.setattr(ext, "inject", _inject_context)
    monkeypatch.setattr(main, "render_menu", render_after_hidden_retry)

    msg = await ext.output_converter("help", "Alconna fallback")

    assert msg.extract_plain_text() == "hidden result"
    assert [call["show_hidden"] for call in calls] == [False, True]


async def test_help_interception_falls_back_after_both_normal_misses(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0013 returns Alconna output when neither PicMenu attempt has a view."""
    from nonebot_plugin_picmenu_next import __main__ as main

    command = _owned_command("missing-picmenu", "missing_plugin")
    ext = main.PMNHelpExtension()
    ext.command = command
    attempts: list[bool] = []

    async def no_view(*_args: object, **kwargs: object) -> object:
        attempts.append(cast("bool", kwargs["show_hidden"]))
        return None, None, None

    monkeypatch.setattr(ext, "inject", _inject_context)
    monkeypatch.setattr(main, "render_menu", no_view)

    msg = await ext.output_converter("help", "Alconna fallback")

    assert msg.extract_plain_text() == "Alconna fallback"
    assert attempts == [False, True]


async def test_help_interception_uses_hidden_snapshot_for_adapter_hidden_plugin(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """Current-command Help renders adapter-hidden targets from the -H snapshot."""
    from nonebot_plugin_alconna.uniseg import UniMessage
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import (
        PMDataItem,
        PMNData,
        PMNPluginInfo,
    )

    command = _owned_command("adapter-hidden-picmenu", "adapter_hidden_plugin")
    item = PMDataItem(
        func="current command",
        trigger_method="adapter-hidden-picmenu",
        trigger_condition="command",
        brief_des="brief",
        detail_des="detail",
    )
    item._alc_cmd_id = command.path  # noqa: SLF001 - Pydantic v1 needs direct assignment
    info = PMNPluginInfo(
        name="adapter hidden",
        plugin_id="adapter_hidden_plugin",
        pm_data=[item],
        pmn=PMNData(template="adapter-hidden-index"),
        supported_adapters=set(),
    )
    rendered: dict[str, object] = {}

    async def render_current_help(
        _info: PMNPluginInfo,
        info_index: int,
        _func: PMDataItem,
        _func_index: int | None,
        showing_hidden: bool,
        _user_can_see_hidden: bool | None,
    ) -> UniMessage:
        rendered["info_index"] = info_index
        rendered["showing_hidden"] = showing_hidden
        return UniMessage("PicMenu current-command help")

    ext = main.PMNHelpExtension()
    ext.command = command
    monkeypatch.setattr(ext, "inject", _inject_context)
    monkeypatch.setattr(main, "get_infos", lambda: [info])
    monkeypatch.setitem(
        main.func_detail_templates.data,
        "adapter-hidden-index",
        render_current_help,
    )

    msg = await ext.output_converter("help", "Alconna fallback")

    assert msg.extract_plain_text() == "PicMenu current-command help"
    assert rendered["info_index"] == 0
    assert rendered["showing_hidden"] is True


async def test_help_interception_logs_render_failure_and_falls_back(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0013 treats a rendering exception as one failed interception operation."""
    from nonebot_plugin_picmenu_next import __main__ as main

    command = _owned_command("render-failure-picmenu", "render_failure_plugin")
    ext = main.PMNHelpExtension()
    ext.command = command
    attempts = 0
    logged_context: list[tuple[object, ...]] = []

    async def fail_render(*_args: object, **_kwargs: object) -> object:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("render failure")

    def capture_exception(_message: str, *args: object) -> None:
        logged_context.append(args)

    monkeypatch.setattr(ext, "inject", _inject_context)
    monkeypatch.setattr(main, "render_menu", fail_render)
    monkeypatch.setattr(main.logger, "exception", capture_exception)

    msg = await ext.output_converter("help", "Alconna fallback")

    assert msg.extract_plain_text() == "Alconna fallback"
    assert attempts == 1
    assert logged_context == [(command.path, "render_failure_plugin")]


async def test_help_interception_logs_context_failure_and_falls_back(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0013 protects dependency injection before rendering starts."""
    from nonebot_plugin_picmenu_next import __main__ as main

    command = _owned_command("context-failure-picmenu", "context_failure_plugin")
    ext = main.PMNHelpExtension()
    ext.command = command
    logged_context: list[tuple[object, ...]] = []

    async def fail_inject(_dependent: object) -> Bot:
        raise RuntimeError("context failure")

    def capture_exception(_message: str, *args: object) -> None:
        logged_context.append(args)

    monkeypatch.setattr(ext, "inject", fail_inject)
    monkeypatch.setattr(main.logger, "exception", capture_exception)

    msg = await ext.output_converter("help", "Alconna fallback")

    assert msg.extract_plain_text() == "Alconna fallback"
    assert logged_context == [(command.path, "context_failure_plugin")]


async def test_help_interception_logs_owner_resolution_failure_and_falls_back(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0013 protects ownership resolution and logs the absent plugin ID."""
    from nonebot_plugin_picmenu_next import __main__ as main

    command = Alconna("owner-failure-picmenu")
    ext = main.PMNHelpExtension()
    ext.command = command
    logged_context: list[tuple[object, ...]] = []

    def fail_owner_resolution(_command: Alconna) -> str:
        raise RuntimeError("owner resolution failure")

    def capture_exception(_message: str, *args: object) -> None:
        logged_context.append(args)

    monkeypatch.setattr(main, "get_alconna_plugin_id", fail_owner_resolution)
    monkeypatch.setattr(main.logger, "exception", capture_exception)

    msg = await ext.output_converter("help", "Alconna fallback")

    assert msg.extract_plain_text() == "Alconna fallback"
    assert logged_context == [(command.path, None)]

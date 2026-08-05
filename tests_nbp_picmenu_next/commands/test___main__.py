"""Tests for the command entry module."""

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, ClassVar, cast

from arclet.alconna import Alconna, CommandMeta, TextFormatter, command_manager
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


def test_help_extension_applies_markdown_formatter_when_registry_is_ready(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """A Markdown-enabled owning plugin replaces Alconna's default formatter."""
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.alconna import PMNMarkdownTextFormatter
    from nonebot_plugin_picmenu_next.data_source.models import PMNData, PMNPluginInfo

    command = _owned_command("formatter-picmenu", "formatter_plugin")
    ext = main.PMNHelpExtension()
    monkeypatch.setattr(
        main,
        "get_infos",
        lambda: [
            PMNPluginInfo(
                name="formatter",
                plugin_id="formatter_plugin",
                pmn=PMNData(markdown=True),
            )
        ],
    )

    assert type(command.formatter) is TextFormatter
    ext.post_init(command)

    assert isinstance(command.formatter, PMNMarkdownTextFormatter)


def test_help_extension_retries_formatter_setup_until_registry_is_ready(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """Formatter setup is retried during validation when startup was too early."""
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.alconna import PMNMarkdownTextFormatter
    from nonebot_plugin_picmenu_next.data_source.models import PMNData, PMNPluginInfo

    command = _owned_command("late-formatter-picmenu", "late_formatter_plugin")
    ext = main.PMNHelpExtension()
    monkeypatch.setattr(main, "get_infos", list)
    ext.post_init(command)
    assert type(command.formatter) is TextFormatter

    monkeypatch.setattr(
        main,
        "get_infos",
        lambda: [
            PMNPluginInfo(
                name="late formatter",
                plugin_id="late_formatter_plugin",
                pmn=PMNData(markdown=True),
            )
        ],
    )
    ext.validate(
        cast("Bot", SimpleNamespace()),
        cast("Event", SimpleNamespace(get_type=lambda: "message")),
    )

    assert isinstance(command.formatter, PMNMarkdownTextFormatter)


def test_help_extension_leaves_default_formatter_for_unowned_or_plain_commands(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """Formatter setup skips commands without an owning Markdown-enabled menu item."""
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMNData, PMNPluginInfo

    unowned = Alconna("unowned-picmenu")
    ext = main.PMNHelpExtension()
    ext.post_init(unowned)
    assert type(unowned.formatter) is TextFormatter

    plain = _owned_command("plain-picmenu", "plain_plugin")
    monkeypatch.setattr(
        main,
        "get_infos",
        lambda: [
            PMNPluginInfo(
                name="plain",
                plugin_id="plain_plugin",
                pmn=PMNData(markdown=False),
            )
        ],
    )
    ext = main.PMNHelpExtension()
    ext.post_init(plain)

    assert type(plain.formatter) is TextFormatter
    assert ext._formatter_checked is True  # noqa: SLF001


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
    assert calls[0]["check_adapter_support"] is False
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


async def test_help_interception_ignores_adapter_filtering(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0007 and ADR-0013 bypass adapter filtering for current-command Help."""
    from nonebot_plugin_alconna.uniseg import UniMessage
    from nonebot_plugin_picmenu_next import __main__ as main

    command = _owned_command("adapter-picmenu", "adapter_plugin")
    ext = main.PMNHelpExtension()
    ext.command = command

    async def render_current_command(*_args: object, **kwargs: object) -> object:
        assert kwargs["check_adapter_support"] is False
        return UniMessage("current command"), None, None

    monkeypatch.setattr(ext, "inject", _inject_context)
    monkeypatch.setattr(main, "render_menu", render_current_command)

    assert (await ext.output_converter("help", "fallback")).extract_plain_text() == (
        "current command"
    )


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
        check_adapter_support=False,
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
        check_adapter_support=False,
    ) == (None, info, None)


def test_global_help_extension_is_disabled_by_default(
    picmenu_plugin: object,
) -> None:
    """ADR-0012 leaves global Alconna Help interception opt-in."""
    from nonebot_plugin_picmenu_next import __main__ as main

    assert main.config.alconna_global_ext is False


def test_adapter_filter_hides_a_copy_without_mutating_source_data(
    picmenu_plugin: object,
) -> None:
    """An unsupported adapter produces a hidden copy and preserves the source item."""
    from nonebot import get_driver
    from nonebot.adapters.satori import Adapter as SatoriAdapter
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(
        name="adapter",
        supported_adapters={"tests.missing_adapter:Adapter"},
    )

    result = main.filter_unsupported_adapters(
        [info],
        SatoriAdapter(get_driver()),
    )

    assert result[0] is not info
    assert result[0].pmn.hidden is True
    assert info.pmn.hidden is False


def test_adapter_filter_accepts_known_variants_and_unknown_support(
    picmenu_plugin: object,
) -> None:
    """Missing adapter data supports all, while each Satori notation resolves alike."""
    from nonebot import get_driver
    from nonebot.adapters.satori import Adapter as SatoriAdapter
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    adapter = SatoriAdapter(get_driver())
    unknown = PMNPluginInfo(name="unknown")
    known = PMNPluginInfo(
        name="known",
        supported_adapters={
            "~satori",
            "nonebot.adapters.satori",
            "nonebot.adapters.satori.adapter:Adapter",
        },
    )

    assert main.filter_unsupported_adapters([unknown], adapter) == [unknown]
    assert main.filter_unsupported_adapters([known], adapter) == [known]


def test_adapter_filter_skips_resolution_when_module_prefix_cannot_match(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """An unrelated adapter entry does not import or resolve an arbitrary module."""
    from nonebot import get_driver
    from nonebot.adapters.satori import Adapter as SatoriAdapter
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    def fail_resolution(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("unrelated adapter must not be resolved")

    monkeypatch.setattr(main, "resolve_dot_notation", fail_resolution)
    info = PMNPluginInfo(
        name="adapter",
        supported_adapters={"tests.missing_adapter:Adapter"},
    )

    result = main.filter_unsupported_adapters([info], SatoriAdapter(get_driver()))

    assert result[0].pmn.hidden is True


def test_help_command_keeps_public_names_and_show_hidden_option(
    picmenu_plugin: object,
) -> None:
    """ADR-0001 and ADR-0003 keep fixed aliases and the public -H option."""
    from nonebot import get_driver
    from nonebot_plugin_picmenu_next import __main__ as main

    command_start = next(iter(get_driver().config.command_start))

    assert main.alc.command == "help"
    assert main.alc.parse(f"{command_start}help").matched
    assert main.alc.parse(f"{command_start}帮助").matched
    assert main.alc.parse(f"{command_start}菜单").matched
    assert main.alc.parse(f"{command_start}help -H").query("show-hidden.value") is True


async def test_menu_queries_prioritize_valid_snapshot_indexes(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0002 resolves an in-range index before fuzzy name and pinyin matching."""
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(name="Bang Zhu", plugin_id="first")
    original = main.get_name_similarities
    monkeypatch.setattr(
        main,
        "get_name_similarities",
        lambda *_args: (_ for _ in ()).throw(AssertionError("fuzzy search used")),
    )

    assert await main.query_plugin([info], "1") == (0, info)

    monkeypatch.setattr(main, "get_name_similarities", lambda *_args: [60])
    assert await main.query_plugin([info], "00") == (0, info)

    monkeypatch.setattr(main, "get_name_similarities", original)
    score_sets = iter([[("name", 100, 0)], [("pinyin", 50, 0)]])
    monkeypatch.setattr(
        main.process,
        "extractWithoutOrder",
        lambda *_args: next(score_sets),
    )
    assert main.get_name_similarities("name", "pinyin", ["name"], ["pinyin"]) == [80]

    monkeypatch.setattr(main, "get_name_similarities", lambda *_args: [59])
    assert await main.query_plugin([info], "missing") is None


async def test_function_queries_support_indexes_and_similarity_thresholds(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """Function queries use snapshot indexes first and retain the score cutoff."""
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMDataItem

    item = PMDataItem(
        func="function",
        trigger_method="function",
        trigger_condition="command",
        brief_des="function",
        detail_des="function",
    )

    assert await main.query_func_detail([item], "1") == (0, item)

    monkeypatch.setattr(main, "get_name_similarities", lambda *_args: [59])
    assert await main.query_func_detail([item], "function") is None

    monkeypatch.setattr(main, "get_name_similarities", lambda *_args: [60])
    assert await main.query_func_detail([item], "function") == (0, item)


async def test_hidden_visibility_policy_can_be_restricted_to_superusers(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0003 defaults hidden discovery to public and allows an operator limit."""
    from nonebot_plugin_picmenu_next import __main__ as main

    monkeypatch.setattr(main.config, "only_superuser_see_hidden", False)
    assert await main.can_user_see_hidden(cast("Any", object()), cast("Any", object()))

    async def reject_superuser(_bot: object, _event: object) -> bool:
        return False

    monkeypatch.setattr(main.config, "only_superuser_see_hidden", True)
    monkeypatch.setattr(main, "SUPERUSER", reject_superuser)

    assert not await main.can_user_see_hidden(
        cast("Any", object()), cast("Any", object())
    )

    async def fail_superuser(_bot: object, _event: object) -> bool:
        raise RuntimeError("permission backend unavailable")

    monkeypatch.setattr(main, "SUPERUSER", fail_superuser)
    assert not await main.can_user_see_hidden(
        cast("Any", object()), cast("Any", object())
    )


async def test_ordinary_menu_omits_hidden_plugins(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0003 removes hidden plugins from ordinary menu discovery."""
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMNData, PMNPluginInfo

    hidden = PMNPluginInfo(
        name="hidden",
        plugin_id="hidden",
        pmn=PMNData(hidden=True),
    )

    async def unchanged(infos: list[PMNPluginInfo]) -> list[PMNPluginInfo]:
        return infos

    monkeypatch.setattr(main, "get_infos", lambda: [hidden])
    monkeypatch.setattr(main, "resolve_main_mixin", unchanged)

    assert await main.render_menu(
        cast("Any", object()),
        cast("Any", object()),
        check_adapter_support=False,
    ) == (None, None, None)


async def test_show_hidden_reveals_adapter_unsupported_plugin(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0003 includes adapter-hidden plugins when -H is requested."""
    from nonebot import get_driver
    from nonebot.adapters.satori import Adapter as SatoriAdapter
    from nonebot_plugin_alconna.uniseg import UniMessage
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    async def unchanged(infos: list[PMNPluginInfo]) -> list[PMNPluginInfo]:
        return infos

    async def render_incompatible(*_args: object, **_kwargs: object) -> UniMessage:
        return UniMessage("adapter-incompatible")

    info = PMNPluginInfo(
        name="incompatible",
        plugin_id="incompatible",
        supported_adapters=set(),
    )
    monkeypatch.setattr(main, "get_infos", lambda: [info])
    monkeypatch.setattr(main, "resolve_main_mixin", unchanged)
    monkeypatch.setitem(main.index_templates.data, "default", render_incompatible)

    result = await main.render_menu(
        cast("Any", SimpleNamespace(adapter=SatoriAdapter(get_driver()))),
        cast("Any", object()),
        show_hidden=True,
    )

    assert result[0] is not None
    assert result[0].extract_plain_text() == "adapter-incompatible"
    assert result[1:] == (None, None)


async def test_show_hidden_reveals_both_plugin_and_function_switches(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0003 permits explicit discovery of hidden plugin functions."""
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

    async def render_func(*_args: object, **_kwargs: object) -> UniMessage:
        return UniMessage("hidden function")

    info = PMNPluginInfo(
        name="hidden",
        plugin_id="hidden",
        pmn=PMNData(hidden=True),
        pm_data=[
            PMDataItem(
                func="hidden function",
                trigger_method="hidden",
                trigger_condition="command",
                brief_des="hidden",
                detail_des="hidden",
                pmn_hidden=True,
            )
        ],
    )
    monkeypatch.setattr(main, "get_infos", lambda: [info])
    monkeypatch.setattr(main, "resolve_main_mixin", unchanged_main)
    monkeypatch.setattr(main, "resolve_detail_mixin", unchanged_detail)
    monkeypatch.setitem(main.func_detail_templates.data, "default", render_func)

    msg, rendered_info, rendered_func = await main.render_menu(
        cast("Any", SimpleNamespace(adapter=SimpleNamespace())),
        cast("Any", object()),
        q_plugin="1",
        q_function="1",
        show_hidden=True,
        check_adapter_support=False,
    )

    assert msg is not None
    assert msg.extract_plain_text() == "hidden function"
    assert rendered_info is info
    assert info.pm_data is not None
    assert rendered_func is info.pm_data[0]


async def test_function_detail_inherits_or_ignores_plugin_template_as_configured(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0014 applies plugin template inheritance only when its switch is enabled."""
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

    async def default(*_args: object, **_kwargs: object) -> UniMessage:
        return UniMessage("default")

    async def inherited(*_args: object, **_kwargs: object) -> UniMessage:
        return UniMessage("inherited")

    def make_info(*, inherit: bool) -> PMNPluginInfo:
        return PMNPluginInfo(
            name="templates",
            pmn=PMNData(template="inherited", inherit_func_template=inherit),
            pm_data=[
                PMDataItem(
                    func="function",
                    trigger_method="function",
                    trigger_condition="command",
                    brief_des="function",
                    detail_des="function",
                )
            ],
        )

    monkeypatch.setattr(main, "resolve_main_mixin", unchanged_main)
    monkeypatch.setattr(main, "resolve_detail_mixin", unchanged_detail)
    monkeypatch.setitem(main.func_detail_templates.data, "default", default)
    monkeypatch.setitem(main.func_detail_templates.data, "inherited", inherited)
    bot = cast("Bot", SimpleNamespace(adapter=SimpleNamespace()))
    event = cast("Event", SimpleNamespace())

    monkeypatch.setattr(main, "get_infos", lambda: [make_info(inherit=True)])
    inherited_message, _, _ = await main.render_menu(
        bot,
        event,
        q_plugin="1",
        q_function="1",
    )
    monkeypatch.setattr(main, "get_infos", lambda: [make_info(inherit=False)])
    default_message, _, _ = await main.render_menu(
        bot,
        event,
        q_plugin="1",
        q_function="1",
    )

    assert inherited_message is not None
    assert inherited_message.extract_plain_text() == "inherited"
    assert default_message is not None
    assert default_message.extract_plain_text() == "default"


async def test_adapter_hiding_can_be_overridden_by_a_later_mixin(
    picmenu_plugin: object,
) -> None:
    """ADR-0007 derives adapter hiding before a later Mixin may replace it."""
    from nonebot import get_driver
    from nonebot.adapters.satori import Adapter as SatoriAdapter
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.mixin import (
        MixinInfo,
        plugin_mixins,
        resolve_main_mixin,
    )
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(
        name="adapter limited",
        supported_adapters={"tests.missing_adapter:Adapter"},
    )
    filtered = main.filter_unsupported_adapters([info], SatoriAdapter(get_driver()))
    original = plugin_mixins.data.copy()

    async def reveal(
        next_chain: Any, infos: list[PMNPluginInfo]
    ) -> list[PMNPluginInfo]:
        infos[0].pmn.hidden = False
        return await next_chain(infos)

    plugin_mixins.data[:] = [MixinInfo(reveal, priority=1, source=None)]
    try:
        resolved = await resolve_main_mixin(filtered)
    finally:
        plugin_mixins.data[:] = original

    assert filtered[0].pmn.hidden is False
    assert resolved[0].pmn.hidden is False


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
        check_adapter_support=False,
    ) == (None, None, None)

    detail, detail_info, detail_func = await main.render_menu(
        bot,
        event,
        plugin_id="plugin",
        check_adapter_support=False,
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
        check_adapter_support=False,
    )
    assert missing is None
    assert missing_info is not None
    assert missing_info.plugin_id == "plugin"
    assert missing_func is None


def test_help_extension_exposes_identity_and_noops_without_a_ready_command(
    picmenu_plugin: object,
) -> None:
    """The help extension has stable metadata and skips uninitialized setup."""
    from nonebot_plugin_picmenu_next import __main__ as main

    extension = main.PMNHelpExtension()
    extension._ensure_markdown_formatter()  # noqa: SLF001

    assert extension.priority == 8
    assert extension.id == "picmenu-next-help"
    assert extension._formatter_checked is False  # noqa: SLF001


async def test_command_handler_finishes_each_user_facing_terminal_path(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """The Help matcher terminates with its dedicated image, message, and text views."""
    import pytest
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMDataItem, PMNPluginInfo

    class FinishedError(Exception):
        pass

    class FakeUniMessage:
        messages: ClassVar[list[str]] = []

        @classmethod
        def image(cls, **_kwargs: object) -> "FakeUniMessage":
            cls.messages.append("image")
            return cls()

        @classmethod
        def text(cls, text: str) -> "FakeUniMessage":
            cls.messages.append(text)
            return cls()

        async def finish(self, **_kwargs: object) -> None:
            raise FinishedError

    class FakeMessage:
        async def finish(self) -> None:
            raise FinishedError

    def query(*, value: object) -> object:
        return SimpleNamespace(result=value)

    async def denied(_bot: object, _event: object) -> bool:
        return False

    async def no_result(*_args: object, **_kwargs: object) -> object:
        return None, None, None

    monkeypatch.setattr(main, "UniMessage", FakeUniMessage)
    monkeypatch.setattr(main.config, "only_superuser_see_hidden", True)
    monkeypatch.setattr(main, "SUPERUSER", denied)
    monkeypatch.setattr(main, "render_menu", no_result)
    with pytest.raises(FinishedError):
        await main._(
            cast("Bot", object()),
            cast("Event", object()),
            query(value=None),
            query(value=None),
            query(value=True),
        )
    assert FakeUniMessage.messages == ["image", "不是主人不给看"]

    monkeypatch.setattr(main.config, "only_superuser_see_hidden", False)
    FakeUniMessage.messages.clear()
    with pytest.raises(FinishedError):
        await main._(
            cast("Bot", object()),
            cast("Event", object()),
            query(value=None),
            query(value=None),
            query(value=False),
        )
    assert FakeUniMessage.messages == ["当前貌似没有任何可用的插件信息呢……"]

    with pytest.raises(FinishedError):
        await main._(
            cast("Bot", object()),
            cast("Event", object()),
            query(value="missing"),
            query(value=None),
            query(value=False),
        )
    assert FakeUniMessage.messages[-1] == "好像没有找到对应插件呢……"

    item = PMDataItem(
        func="function",
        trigger_method="function",
        trigger_condition="command",
        brief_des="brief",
        detail_des="detail",
    )
    info = PMNPluginInfo(name="plugin", pm_data=[item])

    async def missing_function(*_args: object, **_kwargs: object) -> object:
        return None, info, None

    monkeypatch.setattr(main, "render_menu", missing_function)
    with pytest.raises(FinishedError):
        await main._(
            cast("Bot", object()),
            cast("Event", object()),
            query(value="plugin"),
            query(value="missing"),
            query(value=False),
        )
    assert "对应功能" in FakeUniMessage.messages[-1]

    async def no_detail(*_args: object, **_kwargs: object) -> object:
        return None, PMNPluginInfo(name="plugin"), None

    monkeypatch.setattr(main, "render_menu", no_detail)
    with pytest.raises(FinishedError):
        await main._(
            cast("Bot", object()),
            cast("Event", object()),
            query(value="plugin"),
            query(value=None),
            query(value=False),
        )
    assert FakeUniMessage.messages[-1] == "插件 `plugin` 没有详细功能介绍哦"

    async def rendered(*_args: object, **_kwargs: object) -> object:
        return FakeMessage(), PMNPluginInfo(name="plugin"), item

    monkeypatch.setattr(main, "render_menu", rendered)
    with pytest.raises(FinishedError):
        await main._(
            cast("Bot", object()),
            cast("Event", object()),
            query(value="plugin"),
            query(value="function"),
            query(value=False),
        )


def test_global_help_extension_registers_when_explicitly_enabled(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0012 registers the global extension only after an explicit opt-in."""
    import importlib

    import nonebot_plugin_alconna
    from nonebot import get_driver
    from nonebot.adapters.satori import Adapter as SatoriAdapter
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    registered: list[object] = []
    monkeypatch.setattr(
        nonebot_plugin_alconna, "add_global_extension", registered.append
    )
    monkeypatch.setattr(main.config, "alconna_global_ext", True)

    reloaded = importlib.reload(main)

    assert registered == [reloaded.PMNHelpExtension]
    assert reloaded.is_plugin_supported_adapter(
        PMNPluginInfo(name="satori", supported_adapters={"~satori"}),
        SatoriAdapter(get_driver()),
    )

"""Tests for the command entry module."""

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

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


def test_global_help_extension_is_disabled_by_default(
    picmenu_plugin: object,
) -> None:
    """ADR-0012 leaves global Alconna Help interception opt-in."""
    from nonebot_plugin_picmenu_next import __main__ as main

    assert main.config.alconna_global_ext is False


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

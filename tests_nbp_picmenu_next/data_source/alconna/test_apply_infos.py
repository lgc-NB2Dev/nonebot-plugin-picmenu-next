"""Tests for Alconna-derived help data."""

from types import SimpleNamespace
from typing import TYPE_CHECKING

from arclet.alconna import (
    Alconna,
    CommandMeta,
    TextFormatter,
    command_manager,
)

if TYPE_CHECKING:
    import pytest


def teardown_function() -> None:
    for command in command_manager.get_commands():
        if "-picmenu" in command.path:
            command_manager.delete(command)


def _own(command: Alconna, plugin_id: str) -> None:
    command.meta.extra["matcher.source"] = SimpleNamespace(plugin_id=plugin_id)


def test_apply_alconna_command_infos_respects_explicit_function_lists(
    picmenu_plugin: object,
) -> None:
    """ADR-0006 distinguishes omitted, null, empty, and forced function lists."""
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        apply_alconna_command_infos,
    )
    from nonebot_plugin_picmenu_next.data_source.models import (
        PMDataItem,
        PMNData,
        PMNPluginInfo,
    )

    _own(Alconna("omitted-picmenu"), "omitted")
    _own(Alconna("none-picmenu"), "none")
    _own(Alconna("force-picmenu"), "force")
    manual = PMDataItem(
        func="manual",
        trigger_method="manual",
        trigger_condition="command",
        brief_des="manual",
        detail_des="manual",
    )
    infos = apply_alconna_command_infos(
        [
            PMNPluginInfo(name="omitted", plugin_id="omitted"),
            PMNPluginInfo(name="none", plugin_id="none", pm_data=None),
            PMNPluginInfo(name="empty", plugin_id="empty", pm_data=[]),
            PMNPluginInfo(
                name="force",
                plugin_id="force",
                pm_data=[manual],
                pmn=PMNData(alc_force_enable_detect=True),
            ),
        ],
    )

    assert [item.func for item in infos[0].pm_data or []] == ["omitted-picmenu"]
    assert [item.func for item in infos[1].pm_data or []] == ["none-picmenu"]
    assert infos[2].pm_data == []
    assert [item.func for item in infos[3].pm_data or []] == ["force-picmenu", "manual"]


def test_apply_alconna_command_infos_uses_final_markdown_policy(
    picmenu_plugin: object,
) -> None:
    """ADR-0006 applies final Markdown presentation policy to generated entries."""
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        apply_alconna_command_infos,
    )
    from nonebot_plugin_picmenu_next.data_source.models import PMNData, PMNPluginInfo

    command = Alconna(
        "markdown-picmenu",
        meta=CommandMeta(description="Markdown command", usage="markdown-picmenu"),
    )
    _own(command, "markdown_plugin")

    info = apply_alconna_command_infos(
        [
            PMNPluginInfo(
                name="markdown",
                plugin_id="markdown_plugin",
                pmn=PMNData(markdown=True),
            )
        ]
    )[0]

    assert info.pm_data is not None
    assert info.pm_data[0].trigger_method == "`markdown-picmenu`"
    assert "```text" in info.pm_data[0].detail_des


def test_apply_alconna_command_infos_preserves_custom_formatter(
    picmenu_plugin: object,
) -> None:
    """A command-specific formatter remains authoritative for Markdown help."""
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        apply_alconna_command_infos,
    )
    from nonebot_plugin_picmenu_next.data_source.models import PMNData, PMNPluginInfo

    class CustomFormatter(TextFormatter):
        def format_node(self, parts: list | None = None) -> str:  # noqa: ARG002
            return "CUSTOM FORMATTER"

    command = Alconna(
        "custom-picmenu",
        meta=CommandMeta(description="Custom formatter"),
        formatter_type=CustomFormatter,
    )
    _own(command, "custom_plugin")

    info = apply_alconna_command_infos(
        [
            PMNPluginInfo(
                name="custom",
                plugin_id="custom_plugin",
                pmn=PMNData(markdown=True),
            )
        ]
    )[0]

    assert info.pm_data is not None
    assert info.pm_data[0].detail_des == "CUSTOM FORMATTER"


def test_generated_alconna_item_uses_usage_when_help_output_is_empty(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0009 provides a usage fallback when Alconna has no formatted help."""
    from nonebot_plugin_picmenu_next.data_source import alconna

    command = Alconna("usage-fallback-picmenu", meta=CommandMeta(usage="usage <id>"))
    monkeypatch.setattr(alconna, "format_alconna_help_text", lambda *_args: "")

    item = alconna.generate_alconna_menu_item(command)

    assert item.detail_des == "用法：\nusage <id>"

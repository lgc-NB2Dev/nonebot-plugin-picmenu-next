"""Tests for Alconna-derived help data."""

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

from arclet.alconna import (
    Alconna,
    Arg,
    Args,
    CommandMeta,
    Option,
    Subcommand,
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


def test_collect_alconna_menu_data_projects_public_command_surface(
    picmenu_plugin: object,
) -> None:
    """ADR-0009 projects command fields and shortcuts into one function item."""
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        collect_alconna_menu_data,
    )

    command = Alconna(
        "collect-picmenu",
        meta=CommandMeta(
            description="Command description", usage="collect-picmenu <id>"
        ),
    )
    _own(command, "collect_plugin")
    command_manager.add_shortcut(command, "collect-alias", {"prefix": False})

    result = collect_alconna_menu_data({"collect_plugin"}, set())

    assert list(result) == ["collect_plugin"]
    item = result["collect_plugin"][0]
    assert item.func == "collect-picmenu"
    assert item.trigger_method == "collect-picmenu│collect-alias"
    assert item.trigger_condition == "指令"
    assert item.brief_des == "Command description"
    assert "collect-picmenu <id>" in item.detail_des
    assert item.alc_cmd_id == command.path


def test_collect_alconna_menu_data_inherits_command_visibility_and_overrides(
    picmenu_plugin: object,
) -> None:
    """ADR-0008 skips disabled commands and honors explicit PicMenu visibility."""
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        collect_alconna_menu_data,
    )

    hidden = Alconna("hidden-picmenu", meta=CommandMeta(hide=True))
    _own(hidden, "visibility_plugin")
    overridden = Alconna(
        "overridden-picmenu",
        meta=CommandMeta(extra={"pmn": {"pmn_hidden": False}}),
    )
    _own(overridden, "visibility_plugin")
    disabled = Alconna("disabled-picmenu")
    _own(disabled, "visibility_plugin")
    command_manager.set_enabled(disabled, False)
    _unknown = Alconna("unknown-picmenu")

    result = collect_alconna_menu_data({"visibility_plugin"}, set())

    items = {item.func: item for item in result["visibility_plugin"]}
    assert items["hidden-picmenu"].hidden is True
    assert items["overridden-picmenu"].hidden is False
    assert "disabled-picmenu" not in items
    assert "unknown-picmenu" not in items


def test_collect_alconna_menu_data_allows_curated_field_overrides(
    picmenu_plugin: object,
) -> None:
    """ADR-0009 permits an author to override every projected display field."""
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        collect_alconna_menu_data,
    )

    command = Alconna(
        "override-picmenu",
        meta=CommandMeta(
            description="generated",
            extra={
                "pmn": {
                    "func": "Curated",
                    "trigger_method": "custom trigger",
                    "trigger_condition": "custom condition",
                    "brief_des": "custom brief",
                    "detail_des": "custom detail",
                    "pmn_hidden": True,
                    "pmn_template": "plain",
                },
            },
        ),
    )
    _own(command, "override_plugin")

    item = collect_alconna_menu_data({"override_plugin"}, set())["override_plugin"][0]

    assert (
        item.func,
        item.trigger_method,
        item.trigger_condition,
        item.brief_des,
        item.detail_des,
        item.hidden,
        item.template,
    ) == (
        "Curated",
        "custom trigger",
        "custom condition",
        "custom brief",
        "custom detail",
        True,
        "plain",
    )


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


def test_markdown_formatter_formats_subcommands_arguments_and_options(
    picmenu_plugin: object,
) -> None:
    """Generated Markdown help keeps nested command surfaces readable."""
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        format_alconna_help_text,
    )

    command = Alconna(
        "format-picmenu",
        Subcommand(
            "user|用户",
            Subcommand("add|新增", Args["name", str], help_text="Create a user."),
            help_text="User commands.",
        ),
        Args(Arg("count?", int, notice="Count")),
        Option("--role|-r", Args["role", str], help_text="User role."),
        meta=CommandMeta(description="Root command."),
    )

    root = format_alconna_help_text(command, markdown=True)
    nested = format_alconna_help_text(command, markdown=True, parts=["user"])

    assert "- `user`│`用户`" in root
    assert "User commands." in root
    assert "- `add`│`新增` `<name: str>`" in root
    assert "- `count`：类型 `int`，可选；Count" in root
    assert "- `--role`│`-r` `<role: str>`" in root
    assert "User role." in root
    assert "```text\nformat-picmenu user\n```" in nested
    assert "- `add`│`新增` `<name: str>`" in nested
    assert "Create a user." in nested


def test_markdown_formatter_accepts_root_prefixed_help_parts(
    picmenu_plugin: object,
) -> None:
    """Formatter accepts Alconna's command-name and slash-prefixed root parts."""
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        format_alconna_help_text,
    )

    named = Alconna(
        "named-picmenu",
        Subcommand("user", help_text="Users."),
        meta=CommandMeta(description="Named root."),
    )
    slashed = Alconna(
        "/slashed-picmenu",
        Subcommand("user", help_text="Users."),
        meta=CommandMeta(description="Slashed root."),
    )

    assert "Users." in format_alconna_help_text(
        named, markdown=True, parts=["named-picmenu", "user"]
    )
    assert "Slashed root." in format_alconna_help_text(
        slashed, markdown=True, parts=["/slashed-picmenu"]
    )


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


def test_markdown_formatter_covers_arguments_subcommands_and_shortcuts(
    picmenu_plugin: object,
) -> None:
    """Markdown help renders complex argument forms, nested options, and shortcuts."""
    from arclet.alconna.typing import AllParam
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        PMNMarkdownTextFormatter,
        fenced_code,
    )

    command = Alconna(
        "advanced-picmenu",
        Args(
            Arg("same", "same"),
            Arg("all", AllParam),
            Arg("count", int, 1),
            Arg("sep", str, None, ("=", ":")),
            Arg("_key_internal", str),
        ),
        Option("--plain"),
        Subcommand(
            "group",
            Option("--nested", help_text="Nested option."),
            help_text="Group command.",
        ),
        meta=CommandMeta(
            description="Advanced command.",
            usage="advanced-picmenu <value>",
            example="advanced-picmenu demo",
        ),
    )
    command_manager.add_shortcut(
        command,
        "advanced-alias",
        cast("Any", {"prefix": "/", "fuzzy": True, "args": ["fixed"]}),
    )
    formatter = PMNMarkdownTextFormatter().add(command)
    trace = next(iter(formatter.data.values()))
    rendered = formatter.format(trace)

    assert fenced_code("value ``` value").startswith("````text")
    assert "<same>" in rendered
    assert "<...all>" in rendered
    assert "<count: int = 1>" in rendered
    assert "<sep: str = None>['=|:']" in rendered
    assert "_key_internal" not in rendered
    assert "- `--plain`" in rendered
    assert "Nested option." in rendered
    assert "**示例**" in rendered
    assert "**快捷指令**" in rendered
    assert "advanced-alias" in rendered


def test_markdown_formatter_falls_back_and_handles_custom_non_markdown_parts(
    picmenu_plugin: object,
) -> None:
    """Formatter falls back for unknown nodes and defers non-Markdown parts safely."""
    from nonebot_plugin_picmenu_next.data_source import alconna

    class CustomFormatter(TextFormatter):
        def format_node(self, parts: list | None = None) -> str:
            return f"custom:{parts}"

    command = Alconna("custom-parts-picmenu", formatter_type=CustomFormatter)
    formatter = alconna.PMNMarkdownTextFormatter().add(command)
    trace = next(iter(formatter.data.values()))

    assert formatter.find_subcommand(trace.body, []) is None
    assert formatter.format_subcommand_node(trace, ["missing"]) == formatter.format(
        trace
    )
    assert (
        alconna.format_alconna_help_text(command, parts=["part"]) == "custom:['part']"
    )


def test_alconna_projection_handles_invalid_metadata_and_manual_entries(
    picmenu_plugin: object,
) -> None:
    """Invalid overrides fall back to generated data and manual lists remain authoritative."""
    from nonebot_plugin_picmenu_next.data_source import alconna
    from nonebot_plugin_picmenu_next.data_source.models import PMDataItem, PMNPluginInfo

    malformed = Alconna("malformed-picmenu", meta=CommandMeta(extra={"pmn": 1}))
    malformed_item = alconna.generate_alconna_menu_item(malformed)
    manual_command = Alconna("manual-picmenu")
    _own(manual_command, "manual")
    manual = PMDataItem(
        func="manual",
        trigger_method="manual",
        trigger_condition="command",
        brief_des="manual",
        detail_des="manual",
    )
    info = PMNPluginInfo(name="manual", plugin_id="manual", pm_data=[manual])

    result = alconna.apply_alconna_command_infos([info], {"manual"})

    assert malformed_item.func == "malformed-picmenu"
    assert result[0].pm_data == [manual]


def test_markdown_formatter_handles_nested_paths_signatures_and_shortcut_types(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """Formatter resolves nested paths and renders both structured shortcut variants."""
    from arclet.alconna.typing import InnerShortcutArgs
    from nonebot_plugin_picmenu_next.data_source import alconna

    command = Alconna(
        "shortcut-picmenu",
        Subcommand(
            "parent",
            Subcommand("child", Args(Arg("value", str)), help_text="Child command."),
        ),
    )
    formatter = alconna.PMNMarkdownTextFormatter().add(command)
    trace = next(iter(formatter.data.values()))
    structured = InnerShortcutArgs(
        "alias",
        ["shortcut-picmenu"],
        args=["fixed"],
        fuzzy=True,
        prefixes=["/"],
    )
    child = next(node for node in trace.body if isinstance(node, Subcommand))
    nested = next(node for node in child.options if isinstance(node, Subcommand))
    monkeypatch.setattr(
        alconna.command_manager,
        "get_shortcut",
        lambda _command: {"alias": structured},
    )

    found = formatter.find_subcommand(trace.body, ["parent", "child"])

    assert found is not None
    assert found[0] is nested
    assert formatter.subcommand_signature("child", nested) == "child <value: str>"
    assert "`/alias ...args`" in formatter.shortcut({"alias": structured})
    assert formatter.shortcut({"plain": "shortcut-picmenu"}) == (
        "**快捷指令**\n\n- `plain` => `shortcut-picmenu`"
    )
    assert alconna.format_alconna_trigger_method(command, markdown=True) == (
        "`shortcut-picmenu`│`/alias`"
    )

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


def test_markdown_formatter_hides_ignored_nested_options(
    picmenu_plugin: object,
) -> None:
    """Ignored options remain hidden when a subcommand expands in Markdown Help."""
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        PMNMarkdownTextFormatter,
    )

    command = Alconna(
        "ignored-option-picmenu",
        Subcommand(
            "group",
            Option("--visible", help_text="Visible nested option."),
            Option("--ignored", help_text="Ignored nested option."),
        ),
    )
    formatter = PMNMarkdownTextFormatter().add(command)
    formatter.ignore_names.add("--ignored")
    trace = next(iter(formatter.data.values()))

    rendered = formatter.format(trace)

    assert "Visible nested option." in rendered
    assert "Ignored nested option." not in rendered


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

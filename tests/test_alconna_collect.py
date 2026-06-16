from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from arclet.alconna import (
    Alconna,
    Arg,
    Args,
    CommandMeta,
    Option,
    Subcommand,
    TextFormatter,
    command_manager,
    store_true,
)
from nonebot.adapters import Bot, Event

if TYPE_CHECKING:
    import pytest


def teardown_function():
    for command in command_manager.get_commands():
        if "-picmenu" in command.path:
            command_manager.delete(command)


def test_collect_alconna_menu_data_groups_menu_items(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        collect_alconna_menu_data,
    )

    command = Alconna(
        "test-picmenu",
        meta=CommandMeta(description="测试命令", usage="test-picmenu <arg>"),
    )
    command.meta.extra["matcher.source"] = SimpleNamespace(plugin_id="test_plugin")
    command_manager.add_shortcut(command, "alias-picmenu", {"prefix": False})

    other = Alconna("other-picmenu", meta=CommandMeta(description="其他命令"))
    other.meta.extra["matcher.source"] = SimpleNamespace(plugin_id="other_plugin")

    result = collect_alconna_menu_data({"test_plugin", "other_plugin"}, set())

    assert {"test_plugin", "other_plugin"} <= set(result)
    assert len(result["test_plugin"]) == 1
    assert result["test_plugin"][0].func == "test-picmenu"
    assert result["test_plugin"][0].trigger_method == "test-picmenu│alias-picmenu"
    assert result["test_plugin"][0].trigger_condition == "指令"
    assert result["test_plugin"][0].brief_des == "测试命令"
    assert "test-picmenu <arg>" in result["test_plugin"][0].detail_des
    assert result["test_plugin"][0].alc_cmd_id == command.path
    assert result["other_plugin"][0].func == "other-picmenu"

    assert "other_plugin" not in collect_alconna_menu_data({"test_plugin"}, set())


def test_collect_alconna_menu_data_marks_hidden_and_skips_disabled_unknown(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        collect_alconna_menu_data,
    )

    hidden = Alconna(
        "hidden-picmenu",
        meta=CommandMeta(description="隐藏命令", hide=True),
    )
    hidden.meta.extra["matcher.source"] = SimpleNamespace(plugin_id="test_plugin")

    disabled = Alconna(
        "disabled-picmenu",
        meta=CommandMeta(description="禁用命令"),
    )
    disabled.meta.extra["matcher.source"] = SimpleNamespace(plugin_id="test_plugin")
    command_manager.set_enabled(disabled, False)

    _unknown = Alconna("unknown-picmenu", meta=CommandMeta(description="未知来源"))

    result = collect_alconna_menu_data({"test_plugin"}, set())

    assert "test_plugin" in result
    assert "unknown-picmenu" not in {x.func for items in result.values() for x in items}
    assert len(result["test_plugin"]) == 1
    assert result["test_plugin"][0].func == "hidden-picmenu"
    assert result["test_plugin"][0].hidden is True


def test_collect_alconna_menu_data_uses_command_overrides(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        collect_alconna_menu_data,
    )

    command = Alconna(
        "override-picmenu",
        meta=CommandMeta(
            description="覆盖命令",
            usage="override-picmenu",
            extra={
                "pmn": {
                    "func": "覆盖名称",
                    "trigger_method": "覆盖触发方式",
                    "trigger_condition": "覆盖触发条件",
                    "brief_des": "覆盖简要说明",
                    "detail_des": "覆盖详细用法",
                    "pmn_hidden": True,
                    "pmn_template": "plain",
                },
            },
        ),
    )
    command.meta.extra["matcher.source"] = SimpleNamespace(plugin_id="test_plugin")

    result = collect_alconna_menu_data({"test_plugin"}, set())

    assert len(result["test_plugin"]) == 1
    assert result["test_plugin"][0].func == "覆盖名称"
    assert result["test_plugin"][0].trigger_method == "覆盖触发方式"
    assert result["test_plugin"][0].trigger_condition == "覆盖触发条件"
    assert result["test_plugin"][0].brief_des == "覆盖简要说明"
    assert result["test_plugin"][0].detail_des == "覆盖详细用法"
    assert result["test_plugin"][0].hidden is True
    assert result["test_plugin"][0].template == "plain"


def test_collect_alconna_menu_data_ignores_invalid_command_overrides(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        collect_alconna_menu_data,
    )

    command = Alconna(
        "invalid-extra-picmenu",
        meta=CommandMeta(
            description="非法覆盖命令",
            usage="invalid-extra-picmenu",
            extra={"pmn": 1},
        ),
    )
    command.meta.extra["matcher.source"] = SimpleNamespace(plugin_id="test_plugin")

    result = collect_alconna_menu_data({"test_plugin"}, set())

    assert len(result["test_plugin"]) == 1
    assert result["test_plugin"][0].func == "invalid-extra-picmenu"
    assert result["test_plugin"][0].trigger_method == "invalid-extra-picmenu"
    assert result["test_plugin"][0].trigger_condition == "指令"
    assert result["test_plugin"][0].brief_des == "非法覆盖命令"
    assert "invalid-extra-picmenu" in result["test_plugin"][0].detail_des


def test_apply_alconna_command_infos_fills_none_pm_data(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        apply_alconna_command_infos,
    )
    from nonebot_plugin_picmenu_next.data_source.models import (
        PMDataItem,
        PMNPluginInfo,
    )

    auto_command = Alconna("auto-picmenu", meta=CommandMeta(description="自动命令"))
    auto_command.meta.extra["matcher.source"] = SimpleNamespace(
        plugin_id="auto_plugin",
    )
    none_command = Alconna("none-picmenu", meta=CommandMeta(description="None 命令"))
    none_command.meta.extra["matcher.source"] = SimpleNamespace(
        plugin_id="none_plugin",
    )

    auto_info = PMNPluginInfo(name="自动插件", plugin_id="auto_plugin")
    explicit_empty_info = PMNPluginInfo(
        name="空插件",
        plugin_id="empty_plugin",
        pm_data=[],
    )
    explicit_none_info = PMNPluginInfo(
        name="None 插件",
        plugin_id="none_plugin",
        pm_data=None,
    )
    manual_item = PMDataItem(
        func="手动",
        trigger_method="手动触发",
        trigger_condition="手动条件",
        brief_des="手动简介",
        detail_des="手动详情",
    )
    manual_info = PMNPluginInfo(
        name="手动插件",
        plugin_id="manual_plugin",
        pm_data=[manual_item],
    )

    result = apply_alconna_command_infos(
        [auto_info, explicit_empty_info, explicit_none_info, manual_info],
    )

    assert result[0].pm_data is not None
    assert len(result[0].pm_data) == 1
    assert result[0].pm_data[0].func == "auto-picmenu"
    assert result[1].pm_data == []
    assert result[2].pm_data is not None
    assert len(result[2].pm_data) == 1
    assert result[2].pm_data[0].func == "none-picmenu"
    assert result[3].pm_data == [manual_item]


def test_apply_alconna_command_infos_force_prepends_manual_pm_data(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        apply_alconna_command_infos,
    )
    from nonebot_plugin_picmenu_next.data_source.models import (
        PMDataItem,
        PMNData,
        PMNPluginInfo,
    )

    command = Alconna("force-picmenu", meta=CommandMeta(description="强制探测命令"))
    command.meta.extra["matcher.source"] = SimpleNamespace(plugin_id="force_plugin")
    manual_item = PMDataItem(
        func="手写菜单",
        trigger_method="手写触发",
        trigger_condition="手写条件",
        brief_des="手写简介",
        detail_des="手写详情",
    )
    info = PMNPluginInfo(
        name="强制探测插件",
        plugin_id="force_plugin",
        pm_data=[manual_item],
        pmn=PMNData(alc_force_enable_detect=True),
    )

    result = apply_alconna_command_infos([info])

    assert result[0].pm_data is not None
    assert [x.func for x in result[0].pm_data] == ["force-picmenu", "手写菜单"]
    assert result[0].pm_data[1] == manual_item


def test_apply_alconna_command_infos_uses_markdown_formatter(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        apply_alconna_command_infos,
    )
    from nonebot_plugin_picmenu_next.data_source.models import PMNData, PMNPluginInfo

    command = Alconna(
        "markdown-picmenu",
        meta=CommandMeta(
            description="Markdown 命令",
            usage="markdown-picmenu",
            example="markdown-picmenu",
        ),
    )
    command.meta.extra["matcher.source"] = SimpleNamespace(plugin_id="md_plugin")

    result = apply_alconna_command_infos(
        [
            PMNPluginInfo(
                name="Markdown 插件", plugin_id="md_plugin", pmn=PMNData(markdown=True)
            )
        ],
    )

    assert result[0].pm_data is not None
    assert result[0].pm_data[0].trigger_method == "`markdown-picmenu`"
    assert "Markdown 命令" in result[0].pm_data[0].detail_des
    assert "```text" in result[0].pm_data[0].detail_des
    assert "```shell" in result[0].pm_data[0].detail_des


def test_markdown_formatter_displays_direct_subcommand_aliases_readably(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        format_alconna_help_text,
    )

    command = Alconna(
        "sub-picmenu",
        Subcommand(
            "user|用户",
            Subcommand(
                "add|新增",
                Args["name", str],
                Option("--role|-r", Args["role", str], help_text="用户角色。"),
                help_text="新增一个用户。",
            ),
            help_text="用户相关命令。",
        ),
        meta=CommandMeta(usage="sub-picmenu user add <name>"),
    )

    detail_des = format_alconna_help_text(command, markdown=True)

    assert (
        "- `user`│`用户`：用户相关命令。  \n"
        "  该命令下可用的子命令有：\n"
        "  - `add`│`新增` `<name: str>`  \n"
        "    新增一个用户。" in detail_des
    )
    assert "- `user`│`用户`\n  用户相关命令。" not in detail_des
    assert "- `--role <role: str>`" not in detail_des
    assert "`user / 用户 add / 新增" not in detail_des


def test_markdown_formatter_can_format_subcommand_node(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        format_alconna_help_text,
    )

    command = Alconna(
        "sub-node-picmenu",
        Subcommand(
            "user|用户",
            Subcommand(
                "add|新增",
                Args["name", str],
                Option("--role|-r", Args["role", str], help_text="用户角色。"),
                help_text="新增一个用户。",
            ),
            help_text="用户相关命令。",
        ),
    )

    detail_des = format_alconna_help_text(command, markdown=True, parts=["user"])

    assert "```text\nsub-node-picmenu user\n```" in detail_des
    assert (
        "- `add`│`新增` `<name: str>`：新增一个用户。  \n"
        "  该命令下可用的选项有：  \n" in detail_des
    )
    assert "- `add`│`新增` `<name: str>`  \n  新增一个用户。" not in detail_des
    assert "- `--role`│`-r` `<role: str>`：用户角色。" in detail_des
    assert "- `--role <role: str>`（别名：`-r`）\n    用户角色。" not in detail_des


def test_markdown_formatter_formats_nested_subcommands_consistently(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        format_alconna_help_text,
    )

    command = Alconna(
        "sub-nested-picmenu",
        Subcommand(
            "project|项目",
            Subcommand(
                "issue|议题",
                Subcommand(
                    "open|打开",
                    Args["title", str],
                    help_text="打开一个议题。",
                ),
                Subcommand(
                    "close|关闭",
                    help_text="关闭一个议题。",
                ),
                help_text="议题相关三级命令。",
            ),
            help_text="项目相关二级命令。",
        ),
    )

    root_detail_des = format_alconna_help_text(command, markdown=True)
    project_detail_des = format_alconna_help_text(
        command,
        markdown=True,
        parts=["project"],
    )

    expected = (
        "- `issue`│`议题`：议题相关三级命令。  \n"
        "  该命令下可用的子命令有：\n"
        "  - `open`│`打开` `<title: str>`  \n"
        "    打开一个议题。\n"
        "  - `close`│`关闭`  \n"
        "    关闭一个议题。"
    )
    assert (
        "- `project`│`项目`：项目相关二级命令。  \n"
        "  该命令下可用的子命令有：\n"
        "  - `issue`│`议题`  \n"
        "    议题相关三级命令。" in root_detail_des
    )
    assert expected in project_detail_des
    assert "- `issue`│`议题`  \n  议题相关三级命令。" not in project_detail_des


def test_markdown_formatter_formats_args_and_options_inline(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        format_alconna_help_text,
    )

    command = Alconna(
        "inline-picmenu",
        Args(
            Arg("abc?", int, notice="AABBCC"),
            Arg("name", str),
            Arg("name2", str, notice="AABBCC"),
        ),
        Option("--abc|-a", action=store_true),
        Option("--def|-d", action=store_true, help_text="AAA"),
        Option("--upper", Args["u", int], help_text="AAA"),
        Option("--xyz|-x", Args["xyz", str], help_text="AAA"),
    )

    detail_des = format_alconna_help_text(command, markdown=True)

    assert (
        "**参数**\n"
        "\n"
        "- `abc`：类型 `int`，可选；AABBCC\n"
        "- `name`：类型 `str`\n"
        "- `name2`：类型 `str`；AABBCC" in detail_des
    )
    assert (
        "**选项**\n"
        "\n"
        "- `--abc`│`-a`\n"
        "- `--def`│`-d`：AAA\n"
        "- `--upper` `<u: int>`：AAA\n"
        "- `--xyz`│`-x` `<xyz: str>`：AAA" in detail_des
    )


def test_markdown_formatter_accepts_alconna_help_parts_with_command_name(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        format_alconna_help_text,
    )

    command = Alconna(
        "sub-node-picmenu",
        Subcommand(
            "user|用户",
            Subcommand(
                "add|新增",
                Args["name", str],
                help_text="新增一个用户。",
            ),
            help_text="用户相关命令。",
        ),
        meta=CommandMeta(description="根命令说明。"),
    )

    detail_des = format_alconna_help_text(
        command,
        markdown=True,
        parts=["sub-node-picmenu", "user"],
    )

    assert "用户相关命令。" in detail_des
    assert "根命令说明。" not in detail_des
    assert "sub-node-picmenu user" in detail_des


def test_markdown_formatter_accepts_slashed_root_help_parts(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        format_alconna_help_text,
    )

    command = Alconna(
        "/probe-sub",
        Subcommand(
            "user|用户",
            help_text="用户相关命令。",
        ),
        meta=CommandMeta(description="根命令说明。"),
    )

    detail_des = format_alconna_help_text(
        command,
        markdown=True,
        parts=["/probe-sub"],
    )

    assert "根命令说明。" in detail_des
    assert "- `user`│`用户`：用户相关命令。" in detail_des


def test_help_extension_replaces_default_formatter_from_registry(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    from nonebot_plugin_picmenu_next import __main__
    from nonebot_plugin_picmenu_next.data_source.alconna import PMNMarkdownTextFormatter
    from nonebot_plugin_picmenu_next.data_source.models import PMNData, PMNPluginInfo

    command = Alconna("ext-markdown-picmenu")
    command.meta.extra["matcher.source"] = SimpleNamespace(plugin_id="md_plugin")
    ext = __main__.PMNHelpExtension()

    monkeypatch.setattr(
        __main__,
        "get_infos",
        lambda: [
            PMNPluginInfo(
                name="Markdown 插件",
                plugin_id="md_plugin",
                pmn=PMNData(markdown=True),
            ),
        ],
    )

    assert type(command.formatter) is TextFormatter
    ext.post_init(command)
    assert isinstance(command.formatter, PMNMarkdownTextFormatter)


def test_help_extension_retries_formatter_replace_until_registry_ready(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    from nonebot_plugin_picmenu_next import __main__
    from nonebot_plugin_picmenu_next.data_source.alconna import PMNMarkdownTextFormatter
    from nonebot_plugin_picmenu_next.data_source.models import PMNData, PMNPluginInfo

    command = Alconna("ext-late-markdown-picmenu")
    command.meta.extra["matcher.source"] = SimpleNamespace(plugin_id="late_md_plugin")
    ext = __main__.PMNHelpExtension()

    monkeypatch.setattr(__main__, "get_infos", list)
    ext.post_init(command)
    assert type(command.formatter) is TextFormatter

    monkeypatch.setattr(
        __main__,
        "get_infos",
        lambda: [
            PMNPluginInfo(
                name="Late Markdown 插件",
                plugin_id="late_md_plugin",
                pmn=PMNData(markdown=True),
            ),
        ],
    )
    ext.validate(
        cast("Bot", SimpleNamespace()),
        cast("Event", SimpleNamespace(get_type=lambda: "message")),
    )
    assert isinstance(command.formatter, PMNMarkdownTextFormatter)


async def test_help_extension_forces_show_hidden_when_rendering_help(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    from nonebot_plugin_alconna.uniseg import UniMessage
    from nonebot_plugin_picmenu_next import __main__
    from nonebot_plugin_picmenu_next.data_source.models import (
        PMDataItem,
        PMNData,
        PMNPluginInfo,
    )

    command = Alconna("hidden-plugin-picmenu")
    command.meta.extra["matcher.source"] = SimpleNamespace(plugin_id="hidden_plugin")
    ext = __main__.PMNHelpExtension()
    ext.command = command

    async def fake_inject(dependent: object) -> Bot:  # noqa: ARG001
        return cast("Bot", SimpleNamespace(adapter=SimpleNamespace()))

    async def fake_func_detail(
        info: PMNPluginInfo,
        info_index: int,
        func: PMDataItem,
        func_index: int | None,
        showing_hidden: bool,
        user_can_see_hidden: bool | None,
    ) -> UniMessage:
        assert info.name == "隐藏插件"
        assert info_index == 0
        assert func.func == "hidden-plugin-picmenu"
        assert func_index == 0
        assert showing_hidden is True
        assert user_can_see_hidden is True
        return UniMessage("hidden rendered")

    monkeypatch.setattr(ext, "inject", fake_inject)
    item = PMDataItem(
        func="hidden-plugin-picmenu",
        trigger_method="hidden-plugin-picmenu",
        trigger_condition="指令",
        brief_des="隐藏命令",
        detail_des="旧帮助",
    )
    item._alc_cmd_id = command.path  # noqa: SLF001
    monkeypatch.setattr(
        __main__,
        "get_infos",
        lambda: [
            PMNPluginInfo(
                name="隐藏插件",
                plugin_id="hidden_plugin",
                pmn=PMNData(hidden=True),
                pm_data=[item],
            ),
        ],
    )
    monkeypatch.setitem(
        __main__.func_detail_templates.data,
        "default",
        fake_func_detail,
    )

    msg = await ext.output_converter("help", "新帮助")

    assert msg.extract_plain_text() == "hidden rendered"


async def test_help_extension_falls_back_when_plugin_missing(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    from nonebot_plugin_picmenu_next import __main__

    command = Alconna("missing-plugin-picmenu")
    command.meta.extra["matcher.source"] = SimpleNamespace(plugin_id="missing_plugin")
    ext = __main__.PMNHelpExtension()
    ext.command = command

    async def fake_inject(dependent: object) -> Bot:  # noqa: ARG001
        return cast("Bot", SimpleNamespace(adapter=SimpleNamespace()))

    monkeypatch.setattr(ext, "inject", fake_inject)
    monkeypatch.setattr(__main__, "get_infos", list)

    msg = await ext.output_converter("help", "fallback help")

    assert msg.extract_plain_text() == "fallback help"


async def test_help_extension_generates_current_command_when_visible_func_missing(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    from nonebot_plugin_alconna.uniseg import UniMessage
    from nonebot_plugin_picmenu_next import __main__
    from nonebot_plugin_picmenu_next.data_source.models import PMDataItem, PMNPluginInfo

    command = Alconna(
        "visible-missing-func-picmenu",
        meta=CommandMeta(description="可见缺功能命令"),
    )
    command.meta.extra["matcher.source"] = SimpleNamespace(plugin_id="known_plugin")
    ext = __main__.PMNHelpExtension()
    ext.command = command

    async def fake_inject(dependent: object) -> Bot:  # noqa: ARG001
        return cast("Bot", SimpleNamespace(adapter=SimpleNamespace()))

    async def fake_func_detail(
        info: PMNPluginInfo,
        info_index: int,
        func: PMDataItem,
        func_index: int | None,
        showing_hidden: bool,
        user_can_see_hidden: bool | None,
    ) -> UniMessage:
        assert info.name == "已知插件"
        assert info_index == 0
        assert func.func == "visible-missing-func-picmenu"
        assert func.brief_des == "可见缺功能命令"
        assert func.detail_des == "当前帮助"
        assert func_index is None
        assert showing_hidden is True
        assert user_can_see_hidden is True
        return UniMessage("generated visible rendered")

    monkeypatch.setattr(ext, "inject", fake_inject)
    monkeypatch.setattr(
        __main__,
        "get_infos",
        lambda: [
            PMNPluginInfo(
                name="已知插件",
                plugin_id="known_plugin",
                pm_data=[],
            ),
        ],
    )
    monkeypatch.setitem(
        __main__.func_detail_templates.data,
        "default",
        fake_func_detail,
    )

    msg = await ext.output_converter("help", "当前帮助")

    assert msg.extract_plain_text() == "generated visible rendered"


async def test_help_extension_generates_current_command_when_hidden_func_missing(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    from nonebot_plugin_alconna.uniseg import UniMessage
    from nonebot_plugin_picmenu_next import __main__
    from nonebot_plugin_picmenu_next.data_source.models import (
        PMDataItem,
        PMNData,
        PMNPluginInfo,
    )

    command = Alconna(
        "generated-func-picmenu",
        meta=CommandMeta(description="自动生成命令"),
    )
    command.meta.extra["matcher.source"] = SimpleNamespace(plugin_id="hidden_plugin")
    ext = __main__.PMNHelpExtension()
    ext.command = command

    async def fake_inject(dependent: object) -> Bot:  # noqa: ARG001
        return cast("Bot", SimpleNamespace(adapter=SimpleNamespace()))

    async def fake_func_detail(
        info: PMNPluginInfo,
        info_index: int,
        func: PMDataItem,
        func_index: int | None,
        showing_hidden: bool,
        user_can_see_hidden: bool | None,
    ) -> UniMessage:
        assert info.name == "隐藏插件"
        assert info_index == 0
        assert func.func == "generated-func-picmenu"
        assert func.brief_des == "自动生成命令"
        assert func.detail_des == "当前帮助"
        assert func_index is None
        assert showing_hidden is True
        assert user_can_see_hidden is True
        return UniMessage("generated rendered")

    monkeypatch.setattr(ext, "inject", fake_inject)
    monkeypatch.setattr(
        __main__,
        "get_infos",
        lambda: [
            PMNPluginInfo(
                name="隐藏插件",
                plugin_id="hidden_plugin",
                pmn=PMNData(hidden=True),
                pm_data=[],
            ),
        ],
    )
    monkeypatch.setitem(
        __main__.func_detail_templates.data,
        "default",
        fake_func_detail,
    )

    msg = await ext.output_converter("help", "当前帮助")

    assert msg.extract_plain_text() == "generated rendered"


def test_apply_alconna_command_infos_prefers_custom_formatter(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next.data_source.alconna import (
        apply_alconna_command_infos,
    )
    from nonebot_plugin_picmenu_next.data_source.models import PMNData, PMNPluginInfo

    class CustomFormatter(TextFormatter):
        def format_node(self, parts: list | None = None):  # noqa: ARG002
            return "CUSTOM FORMATTER"

    command = Alconna(
        "custom-picmenu",
        meta=CommandMeta(description="自定义 Formatter 命令"),
        formatter_type=CustomFormatter,
    )
    command.meta.extra["matcher.source"] = SimpleNamespace(plugin_id="custom_plugin")

    result = apply_alconna_command_infos(
        [
            PMNPluginInfo(
                name="自定义 Formatter 插件",
                plugin_id="custom_plugin",
                pmn=PMNData(markdown=True),
            )
        ],
    )

    assert result[0].pm_data is not None
    assert result[0].pm_data[0].detail_des == "CUSTOM FORMATTER"


def test_pmn_help_extension_is_disabled_by_default(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next import __main__

    assert __main__.config.alconna_global_ext is False

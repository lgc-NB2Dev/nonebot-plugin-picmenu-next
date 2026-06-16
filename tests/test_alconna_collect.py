from types import SimpleNamespace

from arclet.alconna import Alconna, CommandMeta, TextFormatter, command_manager


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
    assert result[0].pm_data[0].detail_des.startswith("Markdown 命令")
    assert "**指令**" in result[0].pm_data[0].detail_des
    assert "```text" in result[0].pm_data[0].detail_des
    assert "```shell" in result[0].pm_data[0].detail_des


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

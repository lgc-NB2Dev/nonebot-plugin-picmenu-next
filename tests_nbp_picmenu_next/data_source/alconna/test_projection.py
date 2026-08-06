"""Tests for Alconna-derived help data."""

from types import SimpleNamespace

from arclet.alconna import (
    Alconna,
    CommandMeta,
    command_manager,
)


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

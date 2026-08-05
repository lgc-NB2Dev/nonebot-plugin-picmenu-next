from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from arclet.alconna import Alconna, CommandMeta, command_manager
from nonebot.plugin import PluginMetadata

if TYPE_CHECKING:
    import pytest
    from nonebot.plugin import Plugin


def teardown_function() -> None:
    for command in command_manager.get_commands():
        if "-external-menu" in command.path:
            command_manager.delete(command)


def make_menu_item(
    func: str,
):
    from nonebot_plugin_picmenu_next.data_source.models import PMDataItem

    return PMDataItem(
        func=func,
        trigger_method=f"{func} trigger",
        trigger_condition=f"{func} condition",
        brief_des=f"{func} brief",
        detail_des=f"{func} detail",
    )


def make_plugin(
    plugin_id: str,
    metadata: PluginMetadata,
) -> "Plugin":
    return cast(
        "Plugin",
        SimpleNamespace(id_=plugin_id, module_name=plugin_id, metadata=metadata),
    )


def test_external_pmn_merges_only_explicit_nested_fields(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next.data_source.models import (
        ExternalPluginInfo,
        ExternalPMNData,
        PMNData,
        PMNPluginInfo,
    )

    base = PMNPluginInfo(
        name="Base Plugin",
        pmn=PMNData(
            markdown=True,
            template="card",
            inherit_func_template=False,
            alc_force_enable_detect=True,
        ),
    )
    external = ExternalPluginInfo(pmn=ExternalPMNData(hidden=True))

    merged = external.merge_to(base)

    assert merged.pmn.hidden is True
    assert merged.pmn.markdown is True
    assert merged.pmn.template == "card"
    assert merged.pmn.inherit_func_template is False
    assert merged.pmn.alc_force_enable_detect is True


def test_external_empty_pmn_is_noop(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next.data_source.models import (
        ExternalPluginInfo,
        ExternalPMNData,
        PMNData,
        PMNPluginInfo,
    )

    base = PMNPluginInfo(
        name="Base Plugin",
        pmn=PMNData(markdown=True, template="card"),
    )
    external = ExternalPluginInfo(pmn=ExternalPMNData())

    merged = external.merge_to(base)

    assert merged.pmn.markdown is True
    assert merged.pmn.template == "card"


def test_external_func_override_tracks_explicit_empty_list(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next.data_source.models import ExternalPluginInfo

    assert ExternalPluginInfo(funcs=[]).has_func_override() is True
    assert ExternalPluginInfo().has_func_override() is False


def test_external_plugin_omitted_name_uses_plugin_id(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot_plugin_picmenu_next.data_source.models import ExternalPluginInfo

    info = ExternalPluginInfo().to_plugin_info("nonebot_plugin_external_menu")

    assert info.name == "External Menu"
    assert info.plugin_id == "nonebot_plugin_external_menu"


def test_external_config_rejects_disallowed_nulls(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    import pytest
    from cookit.pyd import type_validate_python
    from nonebot_plugin_picmenu_next.data_source.models import ExternalPluginInfo

    for key in ("name", "funcs", "pmn"):
        with pytest.raises(TypeError, match=f"`{key}` cannot be null"):
            type_validate_python(ExternalPluginInfo, {key: None})


def test_external_supported_adapters_accepts_null_but_not_string(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    import pytest
    from cookit.pyd import model_fields_set, type_validate_python
    from nonebot_plugin_picmenu_next.data_source.models import ExternalPluginInfo

    info = type_validate_python(ExternalPluginInfo, {"supported_adapters": None})
    assert "supported_adapters" in model_fields_set(info)
    assert info.supported_adapters is None

    with pytest.raises(TypeError, match="must be an array or null"):
        type_validate_python(ExternalPluginInfo, {"supported_adapters": "~satori"})


async def test_collect_plugin_infos_generates_after_external_markdown_override(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    from nonebot_plugin_picmenu_next.data_source import collect
    from nonebot_plugin_picmenu_next.data_source.models import (
        ExternalPluginInfo,
        ExternalPMNData,
    )

    command = Alconna(
        "markdown-external-menu",
        meta=CommandMeta(description="Markdown 外部覆盖命令"),
    )
    command.meta.extra["matcher.source"] = SimpleNamespace(plugin_id="md_plugin")
    metadata = PluginMetadata(
        name="Markdown Plugin",
        description="desc",
        usage="usage",
        extra={},
    )
    monkeypatch.setattr(
        collect,
        "collect_menus",
        lambda: {"md_plugin": ExternalPluginInfo(pmn=ExternalPMNData(markdown=True))},
    )

    result = await collect.collect_plugin_infos([make_plugin("md_plugin", metadata)])

    assert len(result) == 1
    assert result[0].pmn.markdown is True
    assert result[0].pm_data is not None
    assert result[0].pm_data[0].trigger_method == "`markdown-external-menu`"


async def test_collect_plugin_infos_external_funcs_replace_forced_detection(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    from nonebot_plugin_picmenu_next.data_source import collect
    from nonebot_plugin_picmenu_next.data_source.models import ExternalPluginInfo

    command = Alconna(
        "forced-external-menu",
        meta=CommandMeta(description="强制探测命令"),
    )
    command.meta.extra["matcher.source"] = SimpleNamespace(plugin_id="forced_plugin")
    external_item = make_menu_item("外部功能项")
    metadata = PluginMetadata(
        name="Forced Plugin",
        description="desc",
        usage="usage",
        extra={
            "menu_data": [
                {
                    "func": "手写功能项",
                    "trigger_method": "手写触发",
                    "trigger_condition": "手写条件",
                    "brief_des": "手写简介",
                    "detail_des": "手写详情",
                },
            ],
            "pmn": {"alc_force_enable_detect": True},
        },
    )
    monkeypatch.setattr(
        collect,
        "collect_menus",
        lambda: {"forced_plugin": ExternalPluginInfo(funcs=[external_item])},
    )

    result = await collect.collect_plugin_infos(
        [make_plugin("forced_plugin", metadata)]
    )

    assert len(result) == 1
    assert result[0].pm_data == [external_item]


async def test_collect_plugin_infos_collects_and_overrides_supported_adapters(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    from nonebot_plugin_picmenu_next.data_source import collect
    from nonebot_plugin_picmenu_next.data_source.models import ExternalPluginInfo

    metadata = PluginMetadata(
        name="Adapter Plugin",
        description="desc",
        usage="usage",
        supported_adapters={"~satori"},
        extra={},
    )
    monkeypatch.setattr(
        collect,
        "collect_menus",
        lambda: {
            "adapter_plugin": ExternalPluginInfo(
                supported_adapters={"tests.missing_adapter:Adapter"},
            ),
        },
    )

    result = await collect.collect_plugin_infos(
        [make_plugin("adapter_plugin", metadata)]
    )

    assert len(result) == 1
    assert result[0].supported_adapters == {"tests.missing_adapter:Adapter"}

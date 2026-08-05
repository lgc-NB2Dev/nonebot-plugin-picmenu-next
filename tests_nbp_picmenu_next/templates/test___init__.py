"""Tests for the template registry module."""

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import pytest


def test_template_discovery_and_preloading_collects_all_requested_names(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """Builtin lookup ignores private names and preloads every selected template."""
    from nonebot_plugin_picmenu_next import templates
    from nonebot_plugin_picmenu_next.data_source.models import (
        PMDataItem,
        PMNData,
        PMNPluginInfo,
    )

    loaded: list[str] = []
    info = PMNPluginInfo(
        name="templates",
        pmn=PMNData(template="plugin-template"),
        pm_data=[
            PMDataItem(
                func="function",
                trigger_method="function",
                trigger_condition="command",
                brief_des="function",
                detail_des="function",
                pmn_template="function-template",
            )
        ],
    )
    monkeypatch.setattr(templates, "load_builtin_template", loaded.append)

    assert templates.is_builtin_template("") is False
    assert templates.is_builtin_template("_private") is False
    assert templates.is_builtin_template("default") is True
    templates.preload_builtin_templates_from_infos([info])

    assert set(loaded) == {"plugin-template", "function-template"}


def test_template_selection_falls_back_to_builtin_default(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0014 falls through missing plugin and configured templates to default."""
    from nonebot_plugin_picmenu_next import templates

    fallback = cast("Any", type("Fallback", (), {"name": "default"})())
    collector = templates.TemplateDecoCollector(
        "detail",
        lambda: "missing-user-template",
        data=cast("dict[str, Any]", {"default": fallback}),
    )
    monkeypatch.setattr(templates, "load_builtin_template", lambda _name: False)

    assert collector.get("missing-plugin-template") is fallback
    assert collector.get() is fallback

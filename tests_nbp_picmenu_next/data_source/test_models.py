"""Tests for help-data models."""

import pytest


def test_external_plugin_info_requires_or_derives_a_name(
    picmenu_plugin: object,
) -> None:
    """External data either provides a name or derives one from its file-stem ID."""
    from nonebot_plugin_picmenu_next.data_source.models import ExternalPluginInfo

    with pytest.raises(ValueError, match="`name` is required"):
        ExternalPluginInfo().to_plugin_info()

    info = ExternalPluginInfo().to_plugin_info("nonebot_plugin_menu")

    assert info.name == "Menu"
    assert info.plugin_id == "nonebot_plugin_menu"


def test_external_plugin_info_merges_only_explicit_fields_into_a_copy(
    picmenu_plugin: object,
) -> None:
    """Sparse external data copies the target before replacing declared values."""
    from nonebot_plugin_picmenu_next.data_source.models import (
        ExternalPluginInfo,
        ExternalPMNData,
        PMDataItem,
        PMNData,
        PMNPluginInfo,
    )

    original = PMNPluginInfo(
        name="original",
        plugin_id="original",
        pmn=PMNData(markdown=False),
    )
    func = PMDataItem(
        func="external",
        trigger_method="external",
        trigger_condition="command",
        brief_des="external",
        detail_des="external",
    )
    external = ExternalPluginInfo(
        description="external description",
        funcs=[func],
        pmn=ExternalPMNData(markdown=True),
    )

    merged = external.merge_to(original, plugin_id="merged")

    assert merged is not original
    assert original.description is None
    assert original.pm_data is None
    assert original.pmn.markdown is False
    assert merged.plugin_id == "merged"
    assert merged.description == "external description"
    assert merged.pm_data == [func]
    assert merged.pmn.markdown is True


def test_external_config_cannot_set_plugin_authored_detection_policy(
    picmenu_plugin: object,
) -> None:
    """ADR-0005 prevents external config from enabling forced Alconna detection."""
    from cookit.pyd import type_validate_python
    from nonebot_plugin_picmenu_next.data_source.models import ExternalPluginInfo

    with pytest.raises(TypeError):
        type_validate_python(
            ExternalPluginInfo,
            {"pmn": {"alc_force_enable_detect": True}},
        )


def test_markdown_is_opt_in_for_metadata_and_external_menu_data(
    picmenu_plugin: object,
) -> None:
    """ADR-0015 preserves legacy rich text until Markdown is explicitly enabled."""
    from nonebot_plugin_picmenu_next.data_source.models import ExternalPMNData, PMNData

    assert PMNData().markdown is False
    assert ExternalPMNData().markdown is False


def test_external_pmn_conversion_preserves_only_declared_display_options(
    picmenu_plugin: object,
) -> None:
    """External PMN data converts declared fields without enabling authored policy."""
    from nonebot_plugin_picmenu_next.data_source.models import ExternalPMNData

    converted = ExternalPMNData(hidden=True, template="compact").to_pmn_data()

    assert converted.hidden is True
    assert converted.template == "compact"
    assert converted.alc_force_enable_detect is False


def test_model_validators_accept_model_instances_and_reject_non_mapping_input(
    picmenu_plugin: object,
) -> None:
    """Both external schemas normalize model input but reject scalar configuration."""
    from cookit.pyd import type_validate_python
    from nonebot_plugin_picmenu_next.data_source.models import (
        ExternalPluginInfo,
        PMNPluginExtra,
    )

    extra = PMNPluginExtra(author="Alice")
    external = ExternalPluginInfo(name="External")

    assert type_validate_python(PMNPluginExtra, extra).author == "Alice"
    assert type_validate_python(ExternalPluginInfo, external).name == "External"
    with pytest.raises(TypeError, match="Expected dict"):
        type_validate_python(PMNPluginExtra, 1)
    with pytest.raises(TypeError, match="Expected dict"):
        type_validate_python(ExternalPluginInfo, 1)


def test_optional_and_external_models_convert_name_and_function_data(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """Model conversion validates names, maps funcs, and exposes loaded plugins."""
    from nonebot_plugin_picmenu_next.data_source import models
    from nonebot_plugin_picmenu_next.data_source.models import (
        ExternalPluginInfo,
        OptionalPMNPluginInfo,
        PMDataItem,
        PMNPluginInfo,
    )

    func = PMDataItem(
        func="function",
        trigger_method="function",
        trigger_condition="command",
        brief_des="brief",
        detail_des="detail",
    )
    external = ExternalPluginInfo(name="Configured", funcs=[func])
    converted = external.to_optional_plugin_info("configured")
    sentinel = object()
    info = PMNPluginInfo(name="Plugin", plugin_id="plugin")
    monkeypatch.setattr(models, "get_plugin", lambda _plugin_id: sentinel)

    with pytest.raises(ValueError, match="`name` is required"):
        OptionalPMNPluginInfo().to_required()

    assert converted.plugin_id == "configured"
    assert converted.pm_data == [func]
    assert external.to_plugin_info(name="Explicit").name == "Explicit"
    assert info.plugin is sentinel


def test_optional_conversion_omits_an_explicit_but_empty_pmn_section(
    picmenu_plugin: object,
) -> None:
    """An empty external PMN object does not override a plugin's nested defaults."""
    from cookit.pyd import model_fields_set
    from nonebot_plugin_picmenu_next.data_source.models import (
        ExternalPluginInfo,
        ExternalPMNData,
    )

    converted = ExternalPluginInfo(pmn=ExternalPMNData()).to_optional_plugin_info()

    assert "pmn" not in model_fields_set(converted)


def test_plugin_subtitle_uses_available_author_and_version_fields(
    picmenu_plugin: object,
) -> None:
    """Plugin subtitles omit absent fields and retain their stable display order."""
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    assert PMNPluginInfo(name="none").subtitle == ""
    assert PMNPluginInfo(name="author", author="Alice").subtitle == "By Alice"
    assert PMNPluginInfo(name="version", version="1.0").subtitle == "v1.0"
    assert (
        PMNPluginInfo(name="both", author="Alice", version="1.0").subtitle
        == "By Alice | v1.0"
    )

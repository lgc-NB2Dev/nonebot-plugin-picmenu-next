"""Tests for external help-data collection."""

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from arclet.alconna import command_manager
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


def test_collect_menus_prefers_localstore_config_over_legacy_config(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """The localstore entry wins when both external-menu paths define one ID."""
    from nonebot_plugin_picmenu_next.data_source import collect

    legacy_dir = tmp_path / "menu_config" / "menus"
    localstore_dir = tmp_path / "external_infos"
    legacy_dir.mkdir(parents=True)
    localstore_dir.mkdir()
    (legacy_dir / "shared.json").write_text('{"name": "Legacy"}', encoding="utf-8")
    (localstore_dir / "shared.json").write_text(
        '{"name": "Localstore"}', encoding="utf-8"
    )
    monkeypatch.setattr(collect, "pm_menus_dir", legacy_dir)
    monkeypatch.setattr(collect, "external_infos_dir", localstore_dir)

    infos = collect.collect_menus()

    assert infos["shared"].name == "Localstore"


def test_collect_menus_loads_yaml_and_applies_or_appends_external_infos(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """YAML files load through the optional parser and external data appends by ID."""
    from nonebot_plugin_picmenu_next.data_source import collect
    from nonebot_plugin_picmenu_next.data_source.models import (
        ExternalPluginInfo,
        PMNPluginInfo,
    )

    external_dir = tmp_path / "external_infos"
    external_dir.mkdir()
    (external_dir / "yaml-plugin.yaml").write_text(
        "name: YAML Plugin\n", encoding="utf-8"
    )
    monkeypatch.setattr(collect, "external_infos_dir", external_dir)
    monkeypatch.setattr(collect, "pm_menus_dir", tmp_path / "missing-legacy-dir")

    collected = collect.collect_menus()
    appended = collect.apply_user_custom_infos(
        [], {"new": ExternalPluginInfo(name="New Plugin")}
    )
    existing = PMNPluginInfo(name="Existing", plugin_id="existing")

    assert collected["yaml-plugin"].name == "YAML Plugin"
    assert collect.apply_user_custom_infos([existing], {}) == [existing]
    assert appended[0].plugin_id == "new"
    assert appended[0].name == "New Plugin"


def test_external_pmn_merges_only_explicit_nested_fields(
    picmenu_plugin: object,
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
    picmenu_plugin: object,
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
    picmenu_plugin: object,
) -> None:
    from nonebot_plugin_picmenu_next.data_source.models import ExternalPluginInfo

    assert ExternalPluginInfo(funcs=[]).has_func_override() is True
    assert ExternalPluginInfo().has_func_override() is False


def test_external_plugin_omitted_name_uses_plugin_id(
    picmenu_plugin: object,
) -> None:
    from nonebot_plugin_picmenu_next.data_source.models import ExternalPluginInfo

    info = ExternalPluginInfo().to_plugin_info("nonebot_plugin_external_menu")

    assert info.name == "External Menu"
    assert info.plugin_id == "nonebot_plugin_external_menu"


def test_external_config_rejects_disallowed_nulls(
    picmenu_plugin: object,
) -> None:
    import pytest
    from cookit.pyd import type_validate_python
    from nonebot_plugin_picmenu_next.data_source.models import ExternalPluginInfo
    from pydantic import ValidationError

    for key in ("name", "funcs"):
        with pytest.raises(ValidationError, match=f"`{key}` cannot be null"):
            type_validate_python(ExternalPluginInfo, {key: None})

    with pytest.raises(ValidationError):
        type_validate_python(ExternalPluginInfo, {"pmn": None})


def test_external_supported_adapters_accepts_null_but_not_string(
    picmenu_plugin: object,
) -> None:
    import pytest
    from cookit.pyd import model_fields_set, type_validate_python
    from nonebot_plugin_picmenu_next.data_source.models import ExternalPluginInfo
    from pydantic import ValidationError

    info = type_validate_python(ExternalPluginInfo, {"supported_adapters": None})
    assert "supported_adapters" in model_fields_set(info)
    assert info.supported_adapters is None

    with pytest.raises(ValidationError):
        type_validate_python(ExternalPluginInfo, {"supported_adapters": "~satori"})


def test_collect_menus_recurses_and_applies_nullable_display_overrides(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """ADR-0005 uses recursive file stems and accepts explicit display-value clears."""
    from nonebot_plugin_picmenu_next.data_source import collect
    from nonebot_plugin_picmenu_next.data_source.models import (
        ExternalPluginInfo,
        PMNPluginInfo,
    )

    external_dir = tmp_path / "external_infos"
    (external_dir / "nested").mkdir(parents=True)
    (external_dir / "nested" / "duplicate.json").write_text(
        '{"name": "Nested"}', encoding="utf-8"
    )
    (external_dir / "duplicate.toml").write_text('name = "Top level"', encoding="utf-8")
    monkeypatch.setattr(collect, "external_infos_dir", external_dir)
    monkeypatch.setattr(collect, "pm_menus_dir", tmp_path / "missing-legacy-dir")

    infos = collect.collect_menus()
    overridden = ExternalPluginInfo(description=None, usage=None).merge_to(
        PMNPluginInfo(name="Collected", description="metadata", usage="usage")
    )

    assert set(infos) == {"duplicate"}
    assert infos["duplicate"].name in {"Nested", "Top level"}
    assert overridden.description is None
    assert overridden.usage is None


def test_collect_menus_skips_one_broken_config_file(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """ADR-0010 keeps usable menu data after one individual config file fails."""
    from nonebot_plugin_picmenu_next.data_source import collect

    external_dir = tmp_path / "external_infos"
    external_dir.mkdir()
    (external_dir / "valid.json").write_text('{"name": "Valid"}', encoding="utf-8")
    (external_dir / "broken.json").write_text("{", encoding="utf-8")
    monkeypatch.setattr(collect, "external_infos_dir", external_dir)
    monkeypatch.setattr(collect, "pm_menus_dir", tmp_path / "missing-legacy-dir")

    infos = collect.collect_menus()

    assert infos["valid"].name == "Valid"
    assert "broken" not in infos


def test_collect_menus_skips_an_unreadable_subdirectory(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """An unreadable directory does not block other external menu configs."""
    from nonebot_plugin_picmenu_next.data_source import collect

    external_dir = tmp_path / "external_infos"
    unreadable_dir = external_dir / "unreadable"
    valid_file = external_dir / "valid.json"
    unreadable_dir.mkdir(parents=True)
    valid_file.write_text('{"name": "Valid"}', encoding="utf-8")
    original_iterdir = Path.iterdir

    def iterdir(path: Path):
        if path == external_dir:
            return iter((unreadable_dir, valid_file))
        if path == unreadable_dir:
            raise OSError("directory unavailable")
        return original_iterdir(path)

    monkeypatch.setattr(collect, "external_infos_dir", external_dir)
    monkeypatch.setattr(collect, "pm_menus_dir", tmp_path / "missing-legacy-dir")
    monkeypatch.setattr(Path, "iterdir", iterdir)

    infos = collect.collect_menus()

    assert infos["valid"].name == "Valid"


def test_collect_menus_isolates_an_unreadable_legacy_source(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """ADR-0010 keeps primary data when the legacy source cannot be scanned."""
    from nonebot_plugin_picmenu_next.data_source import collect

    external_dir = tmp_path / "external_infos"
    legacy_dir = tmp_path / "legacy"
    external_dir.mkdir()
    legacy_dir.mkdir()
    (external_dir / "valid.json").write_text('{"name": "Valid"}', encoding="utf-8")
    original_iterdir = Path.iterdir

    def iterdir(path: Path):
        if path == legacy_dir:
            raise OSError("legacy source unavailable")
        return original_iterdir(path)

    monkeypatch.setattr(collect, "external_infos_dir", external_dir)
    monkeypatch.setattr(collect, "pm_menus_dir", legacy_dir)
    monkeypatch.setattr(Path, "iterdir", iterdir)

    infos = collect.collect_menus()

    assert infos["valid"].name == "Valid"


def test_collect_menus_isolates_an_unreadable_primary_source(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """ADR-0005 and ADR-0010 keep legacy data when the primary scan fails."""
    from nonebot_plugin_picmenu_next.data_source import collect

    localstore_dir = tmp_path / "external_infos"
    legacy_dir = tmp_path / "legacy"
    localstore_dir.mkdir()
    legacy_dir.mkdir()
    (legacy_dir / "legacy.json").write_text('{"name": "Legacy"}', encoding="utf-8")
    original_iterdir = Path.iterdir

    def iterdir(path: Path):
        if path == localstore_dir:
            raise OSError("primary source unavailable")
        return original_iterdir(path)

    monkeypatch.setattr(collect, "external_infos_dir", localstore_dir)
    monkeypatch.setattr(collect, "pm_menus_dir", legacy_dir)
    monkeypatch.setattr(Path, "iterdir", iterdir)

    infos = collect.collect_menus()

    assert infos["legacy"].name == "Legacy"

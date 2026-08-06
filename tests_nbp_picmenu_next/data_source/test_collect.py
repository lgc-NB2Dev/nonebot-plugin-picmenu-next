"""Tests for external help-data collection."""

from pathlib import Path
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


def test_collect_helpers_normalize_metadata_and_recurse_to_parent_packages(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """Metadata helpers retain one display author and fall back through parents."""
    from importlib.metadata import PackageNotFoundError

    from nonebot_plugin_picmenu_next.data_source import collect

    distribution = SimpleNamespace(version="2.0", metadata={})
    dist_calls: list[str] = []

    def find_distribution(module_name: str) -> object:
        dist_calls.append(module_name)
        if module_name == "package.child":
            raise PackageNotFoundError(module_name)
        return distribution

    version_calls: list[str] = []

    def import_module(module_name: str) -> object:
        version_calls.append(module_name)
        if module_name == "package.child":
            return SimpleNamespace()
        return SimpleNamespace(__version__="3.0")

    collect.get_dist.cache_clear()
    collect.get_version_attr.cache_clear()
    monkeypatch.setattr(collect, "distribution", find_distribution)
    monkeypatch.setattr(collect.importlib, "import_module", import_module)

    assert collect.normalize_metadata_user("Alice <a>, Bob <b>") == "Alice"
    assert collect.normalize_metadata_user("Alice <a>, Bob <b>", allow_multi=True) == (
        "Alice & Bob"
    )
    assert collect.get_dist("package.child") is distribution
    assert dist_calls == ["package.child", "package"]
    assert collect.get_version_attr("package.child") == "3.0"
    assert version_calls == ["package.child", "package"]


async def test_plugin_metadata_falls_back_to_distribution_version_and_author(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """Plugin discovery uses distribution metadata when module metadata is absent."""
    from nonebot_plugin_picmenu_next.data_source import collect

    distribution = SimpleNamespace(
        version="4.0",
        metadata={"Author": "Alice <alice@example.com>, Bob <bob@example.com>"},
    )
    monkeypatch.setattr(collect, "get_version_attr", lambda _name: None)
    monkeypatch.setattr(collect, "get_dist", lambda _name: distribution)

    info = await collect.get_info_from_plugin(
        cast(
            "Plugin",
            SimpleNamespace(
                id_="distribution_plugin",
                module_name="distribution.plugin",
                metadata=None,
            ),
        )
    )

    assert info.version == "4.0"
    assert info.author == "Alice"


async def test_plugin_metadata_normalizes_picmenu_extra_at_collection_boundary(
    picmenu_plugin: object,
) -> None:
    """Collection accepts the legacy capitalized author key in metadata extras."""
    from nonebot_plugin_picmenu_next.data_source import collect

    metadata = PluginMetadata(
        name="Capitalized Author",
        description="description",
        usage="usage",
        extra={"Author": "Alice"},
    )

    info = await collect.get_info_from_plugin(
        make_plugin("capitalized_author", metadata),
    )

    assert info.author == "Alice"


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


async def test_collect_plugin_infos_generates_after_external_markdown_override(
    picmenu_plugin: object,
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
    picmenu_plugin: object,
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
    picmenu_plugin: object,
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


async def test_collect_plugin_infos_keeps_invalid_picmenu_metadata_plugin(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0010 ignores only invalid PicMenu metadata, not its loaded plugin."""
    from nonebot_plugin_picmenu_next.data_source import collect

    broken = make_plugin(
        "broken_plugin",
        PluginMetadata(
            name="Broken",
            description="broken metadata",
            usage="broken usage",
            extra={"pmn": 1},
        ),
    )
    valid = make_plugin(
        "valid_plugin",
        PluginMetadata(
            name="Valid",
            description="valid metadata",
            usage="valid usage",
            extra={},
        ),
    )
    monkeypatch.setattr(collect, "collect_menus", dict)

    infos = await collect.collect_plugin_infos([broken, valid])

    assert [info.plugin_id for info in infos] == ["broken_plugin", "valid_plugin"]
    assert infos[0].name == "Broken"
    assert infos[0].description == "broken metadata"
    assert infos[0].usage == "broken usage"
    assert infos[0].pm_data is None


async def test_loaded_plugins_keep_display_metadata_fallbacks(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0003 and ADR-0004 retain library and metadata-less plugin display data."""
    from nonebot_plugin_picmenu_next.data_source import collect

    library = await collect.get_info_from_plugin(
        make_plugin(
            "library_plugin",
            PluginMetadata(
                name="Library",
                description="plugin description",
                usage="library usage",
                type="library",
                extra={"author": ["Alice", "Bob"], "version": "1.2.3"},
            ),
        )
    )
    explicitly_visible_library = await collect.get_info_from_plugin(
        make_plugin(
            "visible_library",
            PluginMetadata(
                name="Visible library",
                description="description",
                usage="usage",
                type="library",
                extra={"pmn": {"hidden": False}},
            ),
        )
    )
    distribution = SimpleNamespace(
        version="distribution-version",
        metadata={
            "Summary": "distribution summary",
            "Author-Email": "Carol <carol@example.com>, Dan <dan@example.com>",
        },
    )
    monkeypatch.setattr(collect, "get_version_attr", lambda _name: "module-version")
    monkeypatch.setattr(collect, "get_dist", lambda _name: distribution)
    metadata_less = await collect.get_info_from_plugin(
        cast(
            "Plugin",
            SimpleNamespace(
                id_="metadata_less_plugin",
                module_name="metadata_less.module",
                metadata=None,
            ),
        )
    )

    assert library.pmn.hidden is True
    assert explicitly_visible_library.pmn.hidden is False
    assert library.version == "1.2.3"
    assert library.author == "Alice & Bob"
    assert library.description == "plugin description"
    assert metadata_less.plugin_id == "metadata_less_plugin"
    assert metadata_less.version == "module-version"
    assert metadata_less.author == "Carol & Dan"
    assert metadata_less.description == "distribution summary"

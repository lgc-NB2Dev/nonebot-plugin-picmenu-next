from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

from nonebot.plugin import PluginMetadata

if TYPE_CHECKING:
    import pytest


def _make_plugin(
    plugin_id: str,
    metadata: PluginMetadata | None,
    module_name: str | None = None,
) -> Any:
    return SimpleNamespace(
        id_=plugin_id,
        module_name=module_name or plugin_id,
        metadata=metadata,
    )


def test_external_menu_collection_recurses_and_uses_nullable_display_overrides(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """ADR-0005 treats nested filenames as IDs and permits null display clears."""
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


def test_collect_menus_skips_broken_config_file(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """ADR-0010 keeps valid external menu data after another config file fails."""
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


def test_collect_menus_isolates_an_unreadable_menu_source(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """ADR-0010 requires one unavailable menu source not to block other sources."""
    from nonebot_plugin_picmenu_next.data_source import collect

    external_dir = tmp_path / "external_infos"
    legacy_dir = tmp_path / "legacy"
    external_dir.mkdir()
    legacy_dir.mkdir()
    (external_dir / "valid.json").write_text('{"name": "Valid"}', encoding="utf-8")
    scan_path = collect.scan_path

    def fail_for_legacy(path: Path, suffixes: Any = None):
        if path == legacy_dir:
            raise OSError("legacy source is unavailable")
        yield from scan_path(path, suffixes)

    monkeypatch.setattr(collect, "external_infos_dir", external_dir)
    monkeypatch.setattr(collect, "pm_menus_dir", legacy_dir)
    monkeypatch.setattr(collect, "scan_path", fail_for_legacy)

    infos = collect.collect_menus()

    assert infos["valid"].name == "Valid"


async def test_failed_mixin_keeps_earlier_mutations_and_continues(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    """ADR-0010 preserves a failed Mixin's prior changes and runs the fallback chain."""
    from nonebot_plugin_picmenu_next.data_source.mixin import MixinInfo, chain_mixins

    async def broken_mixin(_next_chain: Any, value: list[str]) -> list[str]:
        value.append("before-error")
        raise RuntimeError("broken mixin")

    async def following_mixin(next_chain: Any, value: list[str]) -> list[str]:
        value.append("following")
        return await next_chain(value)

    async def final_mixin(value: list[str]) -> list[str]:
        value.append("final")
        return value

    chain = chain_mixins(
        [
            MixinInfo(broken_mixin, priority=1, source=None),
            MixinInfo(following_mixin, priority=2, source=None),
        ],
        final_mixin,
    )

    assert await chain([]) == ["before-error", "following", "final"]


async def test_collect_plugin_infos_keeps_plugin_with_invalid_picmenu_metadata(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0010 warns and keeps a plugin with invalid PicMenu metadata."""
    from nonebot_plugin_picmenu_next.data_source import collect

    broken = _make_plugin(
        "broken_plugin",
        PluginMetadata(
            name="Broken",
            description="broken metadata",
            usage="broken usage",
            extra={"pmn": 1},
        ),
    )
    valid = _make_plugin(
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


async def test_mixins_follow_priority_and_keep_equal_priority_order(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    """ADR-0011 nests lower priorities outside higher priorities stably."""
    from nonebot_plugin_picmenu_next.data_source.mixin import (
        MixinCollector,
        chain_mixins,
    )

    events: list[str] = []
    collector = MixinCollector()
    source = cast("Any", SimpleNamespace(plugin_id="test"))

    @collector(priority=2, _matcher_source=source)
    async def first_equal(next_chain: Any, value: str) -> str:
        events.append("first-enter")
        result = await next_chain(value)
        events.append("first-exit")
        return result

    @collector(priority=2, _matcher_source=source)
    async def second_equal(next_chain: Any, value: str) -> str:
        events.append("second-enter")
        result = await next_chain(value)
        events.append("second-exit")
        return result

    @collector(priority=1, _matcher_source=source)
    async def outer(next_chain: Any, value: str) -> str:
        events.append("outer-enter")
        result = await next_chain(value)
        events.append("outer-exit")
        return result

    async def final_mixin(value: str) -> str:
        events.append("final")
        return value

    assert [info.priority for info in collector.data] == [1, 2, 2]
    assert await chain_mixins(collector.data, final_mixin)("result") == "result"
    assert events == [
        "outer-enter",
        "first-enter",
        "second-enter",
        "final",
        "second-exit",
        "first-exit",
        "outer-exit",
    ]


async def test_adapter_hiding_can_be_overridden_by_a_later_mixin(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    """ADR-0007 derives adapter visibility before Mixins may explicitly replace it."""
    from nonebot import get_driver
    from nonebot.adapters.satori import Adapter as SatoriAdapter
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.mixin import (
        MixinInfo,
        plugin_mixins,
        resolve_main_mixin,
    )
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(
        name="Adapter limited",
        supported_adapters={"tests.missing_adapter:Adapter"},
    )
    filtered = main.filter_unsupported_adapters([info], SatoriAdapter(get_driver()))
    original_mixins = plugin_mixins.data.copy()

    async def reveal_adapter_hidden(
        next_chain: Any, infos: list[PMNPluginInfo]
    ) -> list[PMNPluginInfo]:
        infos[0].pmn.hidden = False
        return await next_chain(infos)

    plugin_mixins.data[:] = [
        MixinInfo(reveal_adapter_hidden, priority=1, source=None),
    ]
    try:
        resolved = await resolve_main_mixin(filtered)
    finally:
        plugin_mixins.data[:] = original_mixins

    assert filtered[0].pmn.hidden is False
    assert resolved[0].pmn.hidden is False


def test_template_selection_falls_back_to_the_builtin_default(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0014 falls through missing plugin and user templates to default."""
    from nonebot_plugin_picmenu_next import templates

    fallback = SimpleNamespace(name="default")
    collector = templates.TemplateDecoCollector(
        "detail",
        lambda: "missing-user-template",
        data=cast("dict[str, Any]", {"default": fallback}),
    )
    monkeypatch.setattr(templates, "load_builtin_template", lambda _name: False)

    assert collector.get("missing-plugin-template") is fallback
    assert collector.get() is fallback


async def test_collects_library_and_metadata_less_plugins_with_display_fallbacks(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0003 and ADR-0004 retain useful plugin menu metadata."""
    from nonebot_plugin_picmenu_next.data_source import collect

    library_metadata = PluginMetadata(
        name="Library",
        description="plugin description",
        usage="library usage",
        type="library",
        extra={"author": ["Alice", "Bob"], "version": "1.2.3"},
    )
    library_info = await collect.get_info_from_plugin(
        _make_plugin("library_plugin", library_metadata)
    )

    distribution = SimpleNamespace(
        version="distribution-version",
        metadata={
            "Summary": "distribution summary",
            "Author-Email": "Carol <carol@example.com>, Dan <dan@example.com>",
        },
    )
    monkeypatch.setattr(
        collect, "get_version_attr", lambda _module_name: "module-version"
    )
    monkeypatch.setattr(collect, "get_dist", lambda _module_name: distribution)
    metadata_less_info = await collect.get_info_from_plugin(
        _make_plugin("metadata_less_plugin", None, "metadata_less.module")
    )

    assert library_info.pmn.hidden is True
    assert library_info.version == "1.2.3"
    assert library_info.author == "Alice & Bob"
    assert library_info.description == "plugin description"
    assert metadata_less_info.plugin_id == "metadata_less_plugin"
    assert metadata_less_info.version == "module-version"
    assert metadata_less_info.author == "Carol & Dan"
    assert metadata_less_info.description == "distribution summary"


def test_plugin_self_resource_uses_the_rendered_plugin(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """ADR-0016 resolves plugin:self from the rendered help subject."""
    from nonebot_plugin_picmenu_next import markdown
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    rendered_root = tmp_path / "rendered"
    authored_root = tmp_path / "authored"
    rendered_root.mkdir()
    authored_root.mkdir()
    (rendered_root / "asset.txt").write_text("rendered", encoding="utf-8")
    (authored_root / "asset.txt").write_text("authored", encoding="utf-8")
    plugins = {
        "rendered_plugin": SimpleNamespace(
            module=SimpleNamespace(__path__=[rendered_root])
        ),
        "authored_plugin": SimpleNamespace(
            module=SimpleNamespace(__path__=[authored_root])
        ),
    }
    monkeypatch.setattr(markdown, "get_plugin", plugins.get)
    processor = markdown.build_default_prp_processor(
        lambda _path, module_path, _info, _plugin: module_path.name
    )

    result = processor(
        PMNPluginInfo(name="Rendered", plugin_id="rendered_plugin"),
        "plugin:self,asset.txt",
    )

    assert result == "rendered"


async def test_menu_query_keeps_index_first_and_uses_name_pinyin_fuzzy_matching(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0002 keeps positive indexes ahead of 60/40 name-pinyin matching."""
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    infos = [PMNPluginInfo(name="Bang Zhu", plugin_id="first")]
    get_name_similarities = main.get_name_similarities

    monkeypatch.setattr(
        main,
        "get_name_similarities",
        lambda *_args: (_ for _ in ()).throw(AssertionError("index used fuzzy search")),
    )
    assert await main.query_plugin(infos, "1") == (0, infos[0])

    monkeypatch.setattr(main, "get_name_similarities", lambda *_args: [60])
    assert await main.query_plugin(infos, "00") == (0, infos[0])

    monkeypatch.setattr(main, "get_name_similarities", get_name_similarities)

    score_sets = iter(
        [
            [("name", 100, 0)],
            [("pinyin", 50, 0)],
        ]
    )
    monkeypatch.setattr(
        main.process,
        "extractWithoutOrder",
        lambda *_args: next(score_sets),
    )
    assert main.get_name_similarities("name", "pinyin", ["name"], ["pinyin"]) == [80]


def test_legacy_rich_text_renders_and_malformed_content_falls_back_safely(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    """ADR-0015 supports legacy rich text and preserves malformed content safely."""
    from cookit.jinja.filters import safe_layout
    from nonebot_plugin_picmenu_next.templates.jj_utils import build_base_render_kwargs

    layout = build_base_render_kwargs()["layout"]
    valid = str(layout("<ft color=red>legacy</ft>"))
    malformed = "<ft invalid=value>legacy</ft>"

    assert "color: red" in valid
    assert "legacy" in valid
    assert str(layout(malformed)) == str(safe_layout(malformed))


def test_help_command_contract_and_hidden_visibility_policy(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    """ADR-0001 and ADR-0003 keep fixed commands with configurable hidden access."""
    from nonebot import get_driver
    from nonebot_plugin_picmenu_next import __main__ as main

    command_start = next(iter(get_driver().config.command_start))
    assert main.alc.command == "help"
    assert main.alc.parse(f"{command_start}help").matched
    assert main.alc.parse(f"{command_start}帮助").matched
    assert main.alc.parse(f"{command_start}菜单").matched
    assert main.alc.parse(f"{command_start}help -H").query("show-hidden.value") is True


async def test_hidden_visibility_policy_can_be_restricted_to_superusers(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0003 defaults to public hidden discovery and permits superuser restriction."""
    from nonebot_plugin_picmenu_next import __main__ as main

    monkeypatch.setattr(main.config, "only_superuser_see_hidden", False)
    assert await main.can_user_see_hidden(cast("Any", object()), cast("Any", object()))

    async def reject_superuser(_bot: object, _event: object) -> bool:
        return False

    monkeypatch.setattr(main.config, "only_superuser_see_hidden", True)
    monkeypatch.setattr(main, "SUPERUSER", reject_superuser)
    assert not await main.can_user_see_hidden(
        cast("Any", object()), cast("Any", object())
    )


async def test_ordinary_menu_omits_hidden_plugins(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0003 removes hidden plugins from normal menu discovery."""
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMNData, PMNPluginInfo

    hidden_info = PMNPluginInfo(
        name="Hidden", plugin_id="hidden_plugin", pmn=PMNData(hidden=True)
    )

    async def unchanged(infos: list[PMNPluginInfo]) -> list[PMNPluginInfo]:
        return infos

    monkeypatch.setattr(main, "get_infos", lambda: [hidden_info])
    monkeypatch.setattr(main, "resolve_main_mixin", unchanged)

    assert await main.render_menu(
        cast("Any", object()),
        cast("Any", object()),
        check_adapter_support=False,
    ) == (None, None, None)


def test_markdown_and_global_help_interception_are_opt_in(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    """ADR-0012 and ADR-0015 keep global interception and Markdown disabled by default."""
    from cookit.pyd import type_validate_python
    from nonebot_plugin_picmenu_next.config import ConfigModel
    from nonebot_plugin_picmenu_next.data_source.models import ExternalPMNData, PMNData

    assert ConfigModel().alconna_global_ext is False
    assert type_validate_python(
        ConfigModel, {"pmn_alconna_global_ext": True}
    ).alconna_global_ext
    assert PMNData().markdown is False
    assert ExternalPMNData().markdown is False

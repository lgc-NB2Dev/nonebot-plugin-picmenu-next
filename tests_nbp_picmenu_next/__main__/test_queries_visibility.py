"""Tests for the command entry module."""

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

from arclet.alconna import Alconna, CommandMeta, command_manager
from nonebot.adapters import Bot, Event

if TYPE_CHECKING:
    import pytest


def teardown_function() -> None:
    for command in command_manager.get_commands():
        if "-picmenu" in command.path:
            command_manager.delete(command)


def _owned_command(name: str, plugin_id: str) -> Alconna:
    command = Alconna(name, meta=CommandMeta(description=f"{name} description"))
    command.meta.extra["matcher.source"] = SimpleNamespace(plugin_id=plugin_id)
    return command


async def _inject_context(_dependent: object) -> Bot:
    return cast("Bot", SimpleNamespace(adapter=SimpleNamespace()))


def test_adapter_filter_hides_a_copy_without_mutating_source_data(
    picmenu_plugin: object,
) -> None:
    """An unsupported adapter produces a hidden copy and preserves the source item."""
    from nonebot import get_driver
    from nonebot.adapters.satori import Adapter as SatoriAdapter
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(
        name="adapter",
        supported_adapters={"tests.missing_adapter:Adapter"},
    )

    result = main.filter_unsupported_adapters(
        [info],
        SatoriAdapter(get_driver()),
    )

    assert result[0] is not info
    assert result[0].pmn.hidden is True
    assert info.pmn.hidden is False


def test_adapter_filter_accepts_known_variants_and_unknown_support(
    picmenu_plugin: object,
) -> None:
    """Missing adapter data supports all, while each Satori notation resolves alike."""
    from nonebot import get_driver
    from nonebot.adapters.satori import Adapter as SatoriAdapter
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    adapter = SatoriAdapter(get_driver())
    unknown = PMNPluginInfo(name="unknown")
    known = PMNPluginInfo(
        name="known",
        supported_adapters={
            "~satori",
            "nonebot.adapters.satori",
            "nonebot.adapters.satori.adapter:Adapter",
        },
    )

    assert main.filter_unsupported_adapters([unknown], adapter) == [unknown]
    assert main.filter_unsupported_adapters([known], adapter) == [known]


def test_adapter_filter_skips_resolution_when_module_prefix_cannot_match(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """An unrelated adapter entry does not import or resolve an arbitrary module."""
    from nonebot import get_driver
    from nonebot.adapters.satori import Adapter as SatoriAdapter
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    def fail_resolution(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("unrelated adapter must not be resolved")

    monkeypatch.setattr(main, "resolve_dot_notation", fail_resolution)
    info = PMNPluginInfo(
        name="adapter",
        supported_adapters={"tests.missing_adapter:Adapter"},
    )

    result = main.filter_unsupported_adapters([info], SatoriAdapter(get_driver()))

    assert result[0].pmn.hidden is True


async def test_menu_queries_prioritize_valid_snapshot_indexes(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0002 resolves an in-range index before fuzzy name and pinyin matching."""
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(name="Bang Zhu", plugin_id="first")
    original = main.get_name_similarities
    monkeypatch.setattr(
        main,
        "get_name_similarities",
        lambda *_args: (_ for _ in ()).throw(AssertionError("fuzzy search used")),
    )

    assert await main.query_plugin([info], "1") == (0, info)

    monkeypatch.setattr(main, "get_name_similarities", lambda *_args: [60])
    assert await main.query_plugin([info], "00") == (0, info)

    monkeypatch.setattr(main, "get_name_similarities", original)
    score_sets = iter([[("name", 100, 0)], [("pinyin", 50, 0)]])
    monkeypatch.setattr(
        main.process,
        "extractWithoutOrder",
        lambda *_args: next(score_sets),
    )
    assert main.get_name_similarities("name", "pinyin", ["name"], ["pinyin"]) == [80]

    monkeypatch.setattr(main, "get_name_similarities", lambda *_args: [59])
    assert await main.query_plugin([info], "missing") is None


async def test_function_queries_support_indexes_and_similarity_thresholds(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """Function queries use snapshot indexes first and retain the score cutoff."""
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMDataItem

    item = PMDataItem(
        func="function",
        trigger_method="function",
        trigger_condition="command",
        brief_des="function",
        detail_des="function",
    )

    assert await main.query_func_detail([item], "1") == (0, item)

    monkeypatch.setattr(main, "get_name_similarities", lambda *_args: [59])
    assert await main.query_func_detail([item], "function") is None

    monkeypatch.setattr(main, "get_name_similarities", lambda *_args: [60])
    assert await main.query_func_detail([item], "function") == (0, item)


async def test_hidden_visibility_policy_can_be_restricted_to_superusers(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0003 defaults hidden discovery to public and allows an operator limit."""
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

    async def fail_superuser(_bot: object, _event: object) -> bool:
        raise RuntimeError("permission backend unavailable")

    monkeypatch.setattr(main, "SUPERUSER", fail_superuser)
    assert not await main.can_user_see_hidden(
        cast("Any", object()), cast("Any", object())
    )


async def test_ordinary_menu_omits_hidden_plugins(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0003 removes hidden plugins from ordinary menu discovery."""
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMNData, PMNPluginInfo

    hidden = PMNPluginInfo(
        name="hidden",
        plugin_id="hidden",
        pmn=PMNData(hidden=True),
    )

    async def unchanged(infos: list[PMNPluginInfo]) -> list[PMNPluginInfo]:
        return infos

    monkeypatch.setattr(main, "get_infos", lambda: [hidden])
    monkeypatch.setattr(main, "resolve_main_mixin", unchanged)

    assert await main.render_menu(
        cast("Any", SimpleNamespace(adapter=SimpleNamespace())),
        cast("Any", object()),
    ) == (None, None, None)


async def test_show_hidden_reveals_adapter_unsupported_plugin(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0003 includes adapter-hidden plugins when -H is requested."""
    from nonebot import get_driver
    from nonebot.adapters.satori import Adapter as SatoriAdapter
    from nonebot_plugin_alconna.uniseg import UniMessage
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    async def unchanged(infos: list[PMNPluginInfo]) -> list[PMNPluginInfo]:
        return infos

    async def render_incompatible(*_args: object, **_kwargs: object) -> UniMessage:
        return UniMessage("adapter-incompatible")

    info = PMNPluginInfo(
        name="incompatible",
        plugin_id="incompatible",
        supported_adapters=set(),
    )
    monkeypatch.setattr(main, "get_infos", lambda: [info])
    monkeypatch.setattr(main, "resolve_main_mixin", unchanged)
    monkeypatch.setitem(main.index_templates.data, "default", render_incompatible)

    result = await main.render_menu(
        cast("Any", SimpleNamespace(adapter=SatoriAdapter(get_driver()))),
        cast("Any", object()),
        show_hidden=True,
    )

    assert result[0] is not None
    assert result[0].extract_plain_text() == "adapter-incompatible"
    assert result[1:] == (None, None)


async def test_show_hidden_reveals_both_plugin_and_function_switches(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0003 permits explicit discovery of hidden plugin functions."""
    from nonebot_plugin_alconna.uniseg import UniMessage
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import (
        PMDataItem,
        PMNData,
        PMNPluginInfo,
    )

    async def unchanged_main(infos: list[PMNPluginInfo]) -> list[PMNPluginInfo]:
        return infos

    async def unchanged_detail(info: PMNPluginInfo) -> PMNPluginInfo:
        return info

    async def render_func(*_args: object, **_kwargs: object) -> UniMessage:
        return UniMessage("hidden function")

    info = PMNPluginInfo(
        name="hidden",
        plugin_id="hidden",
        pmn=PMNData(hidden=True),
        pm_data=[
            PMDataItem(
                func="hidden function",
                trigger_method="hidden",
                trigger_condition="command",
                brief_des="hidden",
                detail_des="hidden",
                pmn_hidden=True,
            )
        ],
    )
    monkeypatch.setattr(main, "get_infos", lambda: [info])
    monkeypatch.setattr(main, "resolve_main_mixin", unchanged_main)
    monkeypatch.setattr(main, "resolve_detail_mixin", unchanged_detail)
    monkeypatch.setitem(main.func_detail_templates.data, "default", render_func)

    msg, rendered_info, rendered_func = await main.render_menu(
        cast("Any", SimpleNamespace(adapter=SimpleNamespace())),
        cast("Any", object()),
        q_plugin="1",
        q_function="1",
        show_hidden=True,
    )

    assert msg is not None
    assert msg.extract_plain_text() == "hidden function"
    assert rendered_info is info
    assert info.pm_data is not None
    assert rendered_func is info.pm_data[0]


async def test_function_detail_inherits_or_ignores_plugin_template_as_configured(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """ADR-0014 applies plugin template inheritance only when its switch is enabled."""
    from nonebot_plugin_alconna.uniseg import UniMessage
    from nonebot_plugin_picmenu_next import __main__ as main
    from nonebot_plugin_picmenu_next.data_source.models import (
        PMDataItem,
        PMNData,
        PMNPluginInfo,
    )

    async def unchanged_main(infos: list[PMNPluginInfo]) -> list[PMNPluginInfo]:
        return infos

    async def unchanged_detail(info: PMNPluginInfo) -> PMNPluginInfo:
        return info

    async def default(*_args: object, **_kwargs: object) -> UniMessage:
        return UniMessage("default")

    async def inherited(*_args: object, **_kwargs: object) -> UniMessage:
        return UniMessage("inherited")

    def make_info(*, inherit: bool) -> PMNPluginInfo:
        return PMNPluginInfo(
            name="templates",
            pmn=PMNData(template="inherited", inherit_func_template=inherit),
            pm_data=[
                PMDataItem(
                    func="function",
                    trigger_method="function",
                    trigger_condition="command",
                    brief_des="function",
                    detail_des="function",
                )
            ],
        )

    monkeypatch.setattr(main, "resolve_main_mixin", unchanged_main)
    monkeypatch.setattr(main, "resolve_detail_mixin", unchanged_detail)
    monkeypatch.setitem(main.func_detail_templates.data, "default", default)
    monkeypatch.setitem(main.func_detail_templates.data, "inherited", inherited)
    bot = cast("Bot", SimpleNamespace(adapter=SimpleNamespace()))
    event = cast("Event", SimpleNamespace())

    monkeypatch.setattr(main, "get_infos", lambda: [make_info(inherit=True)])
    inherited_message, _, _ = await main.render_menu(
        bot,
        event,
        q_plugin="1",
        q_function="1",
    )
    monkeypatch.setattr(main, "get_infos", lambda: [make_info(inherit=False)])
    default_message, _, _ = await main.render_menu(
        bot,
        event,
        q_plugin="1",
        q_function="1",
    )

    assert inherited_message is not None
    assert inherited_message.extract_plain_text() == "inherited"
    assert default_message is not None
    assert default_message.extract_plain_text() == "default"


async def test_adapter_hiding_can_be_overridden_by_a_later_mixin(
    picmenu_plugin: object,
) -> None:
    """ADR-0007 derives adapter hiding before a later Mixin may replace it."""
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
        name="adapter limited",
        supported_adapters={"tests.missing_adapter:Adapter"},
    )
    filtered = main.filter_unsupported_adapters([info], SatoriAdapter(get_driver()))
    original = plugin_mixins.data.copy()

    async def reveal(
        next_chain: Any, infos: list[PMNPluginInfo]
    ) -> list[PMNPluginInfo]:
        infos[0].pmn.hidden = False
        return await next_chain(infos)

    plugin_mixins.data[:] = [MixinInfo(reveal, priority=1, source=None)]
    try:
        resolved = await resolve_main_mixin(filtered)
    finally:
        plugin_mixins.data[:] = original

    assert filtered[0].pmn.hidden is False
    assert resolved[0].pmn.hidden is False

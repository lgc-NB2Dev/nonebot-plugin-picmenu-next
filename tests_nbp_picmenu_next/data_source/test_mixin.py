"""Tests for help-data Mixin registration and dispatch."""

from types import SimpleNamespace
from typing import Any, cast

import pytest


def test_mixin_type_aliases_resolve_at_runtime(picmenu_plugin: object) -> None:
    """Mixin extension type aliases resolve while the plugin data source loads."""
    from nonebot_plugin_picmenu_next.data_source import mixin

    assert mixin.PluginCollectMixin is not None
    assert mixin.SelfMixin is not None


def test_self_mixin_registration_requires_an_owning_plugin(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """A self Mixin cannot register when NoneBot supplies no plugin source."""
    from nonebot_plugin_picmenu_next.data_source import mixin

    collector = mixin.SelfMixinCollector()
    monkeypatch.setattr(mixin, "get_matcher_source", lambda: None)

    with pytest.raises(ValueError, match="Self plugin not found"):

        @collector()
        async def invalid_self_mixin(next_chain: Any, value: object) -> object:
            return await next_chain(value)


def test_self_mixin_registration_records_the_owning_plugin_source(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """Self Mixins register under the matcher source's owning plugin ID."""
    from nonebot_plugin_picmenu_next.data_source import mixin

    collector = mixin.SelfMixinCollector()
    source = cast(
        "Any", SimpleNamespace(plugin_id="owner", module_name="module", lineno=1)
    )
    monkeypatch.setattr(mixin, "get_matcher_source", lambda *_args: source)

    @collector(priority=3)
    async def registered(next_chain: Any, value: object) -> object:
        return await next_chain(value)

    assert collector["owner"].data[0].func is registered
    assert collector["owner"].data[0].priority == 3


async def test_main_mixins_apply_external_and_self_dispatch_and_empty_identity(
    picmenu_plugin: object,
) -> None:
    """Main menu Mixins compose globally, per plugin, and preserve empty input."""
    from nonebot_plugin_picmenu_next.data_source import mixin
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    events: list[str] = []
    original_global = mixin.plugin_mixins.data.copy()
    original_self = mixin.self_mixins.get("owner")

    async def global_mixin(
        next_chain: Any,
        infos: list[PMNPluginInfo],
    ) -> list[PMNPluginInfo]:
        events.append("global")
        return await next_chain(infos)

    async def self_mixin(next_chain: Any, info: PMNPluginInfo) -> PMNPluginInfo:
        events.append("self")
        info.description = "resolved"
        return await next_chain(info)

    mixin.plugin_mixins.data[:] = [
        mixin.MixinInfo(global_mixin, priority=1, source=None)
    ]
    mixin.self_mixins["owner"].data[:] = [
        mixin.MixinInfo(self_mixin, priority=1, source=None)
    ]
    try:
        assert await mixin.resolve_main_mixin([]) == []
        result = await mixin.resolve_main_mixin(
            [PMNPluginInfo(name="owner", plugin_id="owner")]
        )
    finally:
        mixin.plugin_mixins.data[:] = original_global
        if original_self is None:
            del mixin.self_mixins["owner"]
        else:
            mixin.self_mixins["owner"] = original_self

    assert events == ["global", "self"]
    assert result[0].description == "resolved"


def test_mixin_source_warnings_include_known_registration_location(
    picmenu_plugin: object,
) -> None:
    """Mixin failures name their source plugin, module, and registration line."""
    from nonebot_plugin_picmenu_next.data_source.mixin import (
        MixinInfo,
        format_source_warn_msg,
    )

    source = cast(
        "Any", SimpleNamespace(plugin_id="owner", module_name="pkg.mod", lineno=7)
    )
    warning = format_source_warn_msg(
        MixinInfo(func=lambda: None, priority=1, source=source)
    )

    assert warning == "Failed to run mixin from plugin owner at module pkg.mod, line 7"


async def test_detail_mixins_run_external_then_self_chains(
    picmenu_plugin: object,
) -> None:
    """Detail rendering applies global and then owning-plugin Mixin chains."""
    from nonebot_plugin_picmenu_next.data_source import mixin
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    events: list[str] = []
    original_global = mixin.plugin_detail_mixins.data.copy()
    original_self = mixin.self_detail_mixins.get("plugin")

    async def global_mixin(
        next_chain: Any,
        info: PMNPluginInfo,
    ) -> PMNPluginInfo:
        events.append("global")
        info.description = "global"
        return await next_chain(info)

    async def self_mixin(
        next_chain: Any,
        info: PMNPluginInfo,
    ) -> PMNPluginInfo:
        events.append("self")
        info.usage = "self"
        return await next_chain(info)

    mixin.plugin_detail_mixins.data[:] = [
        mixin.MixinInfo(global_mixin, priority=1, source=None)
    ]
    mixin.self_detail_mixins["plugin"].data[:] = [
        mixin.MixinInfo(self_mixin, priority=1, source=None)
    ]
    try:
        result = await mixin.resolve_detail_mixin(
            PMNPluginInfo(name="plugin", plugin_id="plugin")
        )
    finally:
        mixin.plugin_detail_mixins.data[:] = original_global
        if original_self is None:
            del mixin.self_detail_mixins["plugin"]
        else:
            mixin.self_detail_mixins["plugin"] = original_self

    assert events == ["global", "self"]
    assert result.description == "global"
    assert result.usage == "self"


async def test_mixin_chain_preserves_mutations_and_priority_nesting(
    picmenu_plugin: object,
) -> None:
    """ADR-0010 and ADR-0011 preserve mutations and nest lower priorities outside."""
    from nonebot_plugin_picmenu_next.data_source.mixin import MixinInfo, chain_mixins

    events: list[str] = []

    async def broken(next_chain: Any, values: list[str]) -> list[str]:
        values.append("before-error")
        events.append("broken-enter")
        raise RuntimeError("broken")

    async def outer(next_chain: Any, values: list[str]) -> list[str]:
        events.append("outer-enter")
        result = await next_chain(values)
        events.append("outer-exit")
        return result

    async def final(values: list[str]) -> list[str]:
        events.append("final")
        return values

    chain = chain_mixins(
        [
            MixinInfo(outer, priority=1, source=None),
            MixinInfo(broken, priority=2, source=None),
        ],
        final,
    )

    assert await chain([]) == ["before-error"]
    assert events == ["outer-enter", "broken-enter", "final", "outer-exit"]


async def test_mixin_collector_preserves_equal_priority_registration_order(
    picmenu_plugin: object,
) -> None:
    """ADR-0011 keeps registration order only for Mixins sharing a priority."""
    from nonebot_plugin_picmenu_next.data_source.mixin import (
        MixinCollector,
        chain_mixins,
    )

    events: list[str] = []
    collector = MixinCollector()
    source = cast("Any", SimpleNamespace(plugin_id="test"))

    @collector(priority=2, _matcher_source=source)
    async def first(next_chain: Any, value: str) -> str:
        events.append("first-enter")
        result = await next_chain(value)
        events.append("first-exit")
        return result

    @collector(priority=2, _matcher_source=source)
    async def second(next_chain: Any, value: str) -> str:
        events.append("second-enter")
        result = await next_chain(value)
        events.append("second-exit")
        return result

    async def final(value: str) -> str:
        events.append("final")
        return value

    assert await chain_mixins(collector.data, final)("result") == "result"
    assert events == [
        "first-enter",
        "second-enter",
        "final",
        "second-exit",
        "first-exit",
    ]

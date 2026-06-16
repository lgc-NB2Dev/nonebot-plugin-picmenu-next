from types import SimpleNamespace
from typing import TYPE_CHECKING

from nonebot.adapters.satori import Adapter as SatoriAdapter
from nonebot.plugin import PluginMetadata

if TYPE_CHECKING:
    import pytest


SUPPORTED_ADAPTER_PATH = "~satori"


def make_plugin(metadata: PluginMetadata):
    return SimpleNamespace(id_="adapter_plugin", metadata=metadata)


def get_fake_plugin(metadata: PluginMetadata):
    def _get_fake_plugin(_info: object):
        return make_plugin(metadata)

    return _get_fake_plugin


def test_filter_unsupported_adapters_hides_copy_only(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    from nonebot import get_driver
    from nonebot_plugin_picmenu_next.__main__ import filter_unsupported_adapters
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(name="Adapter Plugin", plugin_id="adapter_plugin")
    metadata = PluginMetadata(
        name="Adapter Plugin",
        description="desc",
        usage="usage",
        supported_adapters={"tests.missing_adapter:Adapter"},
    )
    monkeypatch.setattr(
        PMNPluginInfo,
        "plugin",
        property(get_fake_plugin(metadata)),
    )

    adapter = SatoriAdapter(get_driver())
    result = filter_unsupported_adapters([info], adapter)

    assert result[0] is not info
    assert result[0].pmn.hidden is True
    assert info.pmn.hidden is False


def test_filter_unsupported_adapters_keeps_supported(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    from nonebot import get_driver
    from nonebot_plugin_picmenu_next.__main__ import filter_unsupported_adapters
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(name="Adapter Plugin", plugin_id="adapter_plugin")
    metadata = PluginMetadata(
        name="Adapter Plugin",
        description="desc",
        usage="usage",
        supported_adapters={SUPPORTED_ADAPTER_PATH},
    )
    monkeypatch.setattr(
        PMNPluginInfo,
        "plugin",
        property(get_fake_plugin(metadata)),
    )

    adapter = SatoriAdapter(get_driver())
    result = filter_unsupported_adapters([info], adapter)

    assert result[0] is info
    assert result[0].pmn.hidden is False


def test_filter_unsupported_adapters_keeps_unknown_support(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    from nonebot import get_driver
    from nonebot_plugin_picmenu_next.__main__ import filter_unsupported_adapters
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(name="Adapter Plugin", plugin_id="adapter_plugin")
    metadata = PluginMetadata(
        name="Adapter Plugin",
        description="desc",
        usage="usage",
        supported_adapters=None,
    )
    monkeypatch.setattr(
        PMNPluginInfo,
        "plugin",
        property(get_fake_plugin(metadata)),
    )

    adapter = SatoriAdapter(get_driver())
    result = filter_unsupported_adapters([info], adapter)

    assert result[0] is info
    assert result[0].pmn.hidden is False


def test_filter_unsupported_adapters_hides_unloaded_adapter(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    from nonebot import get_driver
    from nonebot_plugin_picmenu_next.__main__ import filter_unsupported_adapters
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(name="Adapter Plugin", plugin_id="adapter_plugin")
    metadata = PluginMetadata(
        name="Adapter Plugin",
        description="desc",
        usage="usage",
        supported_adapters={"tests.missing_adapter:Adapter"},
    )
    monkeypatch.setattr(
        PMNPluginInfo,
        "plugin",
        property(get_fake_plugin(metadata)),
    )

    adapter = SatoriAdapter(get_driver())
    result = filter_unsupported_adapters([info], adapter)

    assert result[0] is not info
    assert result[0].pmn.hidden is True


def test_filter_unsupported_adapters_keeps_supported_module_variants(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    from nonebot import get_driver
    from nonebot_plugin_picmenu_next.__main__ import filter_unsupported_adapters
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(name="Adapter Plugin", plugin_id="adapter_plugin")
    metadata = PluginMetadata(
        name="Adapter Plugin",
        description="desc",
        usage="usage",
        supported_adapters={
            "~satori",
            "nonebot.adapters.satori",
            "nonebot.adapters.satori.adapter:Adapter",
        },
    )
    monkeypatch.setattr(
        PMNPluginInfo,
        "plugin",
        property(get_fake_plugin(metadata)),
    )
    adapter = SatoriAdapter(get_driver())
    result = filter_unsupported_adapters([info], adapter)

    assert result[0] is info


def test_filter_unsupported_adapters_skips_import_when_prefix_mismatch(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    from nonebot import get_driver
    from nonebot_plugin_picmenu_next import __main__
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(name="Adapter Plugin", plugin_id="adapter_plugin")
    metadata = PluginMetadata(
        name="Adapter Plugin",
        description="desc",
        usage="usage",
        supported_adapters={"tests.missing_adapter:Adapter"},
    )
    monkeypatch.setattr(
        PMNPluginInfo,
        "plugin",
        property(get_fake_plugin(metadata)),
    )

    def fail_resolve(*_args: object, **_kwargs: object) -> object:
        raise AssertionError

    monkeypatch.setattr(__main__, "resolve_dot_notation", fail_resolve)
    result = __main__.filter_unsupported_adapters([info], SatoriAdapter(get_driver()))

    assert result[0] is not info
    assert result[0].pmn.hidden is True

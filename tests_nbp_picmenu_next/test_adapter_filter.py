from typing import TYPE_CHECKING

from nonebot.adapters.satori import Adapter as SatoriAdapter

if TYPE_CHECKING:
    import pytest


SUPPORTED_ADAPTER_PATH = "~satori"


def test_filter_unsupported_adapters_hides_copy_only(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot import get_driver
    from nonebot_plugin_picmenu_next.__main__ import filter_unsupported_adapters
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(
        name="Adapter Plugin",
        supported_adapters={"tests.missing_adapter:Adapter"},
    )

    adapter = SatoriAdapter(get_driver())
    result = filter_unsupported_adapters([info], adapter)

    assert result[0] is not info
    assert result[0].pmn.hidden is True
    assert info.pmn.hidden is False


def test_filter_unsupported_adapters_keeps_supported(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot import get_driver
    from nonebot_plugin_picmenu_next.__main__ import filter_unsupported_adapters
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(
        name="Adapter Plugin",
        supported_adapters={SUPPORTED_ADAPTER_PATH},
    )

    adapter = SatoriAdapter(get_driver())
    result = filter_unsupported_adapters([info], adapter)

    assert result[0] is info
    assert result[0].pmn.hidden is False


def test_filter_unsupported_adapters_keeps_unknown_support(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot import get_driver
    from nonebot_plugin_picmenu_next.__main__ import filter_unsupported_adapters
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(name="Adapter Plugin", plugin_id="adapter_plugin")

    adapter = SatoriAdapter(get_driver())
    result = filter_unsupported_adapters([info], adapter)

    assert result[0] is info
    assert result[0].pmn.hidden is False


def test_filter_unsupported_adapters_hides_unloaded_adapter(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot import get_driver
    from nonebot_plugin_picmenu_next.__main__ import filter_unsupported_adapters
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(
        name="Adapter Plugin",
        supported_adapters={"tests.missing_adapter:Adapter"},
    )

    adapter = SatoriAdapter(get_driver())
    result = filter_unsupported_adapters([info], adapter)

    assert result[0] is not info
    assert result[0].pmn.hidden is True


def test_filter_unsupported_adapters_keeps_supported_module_variants(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot import get_driver
    from nonebot_plugin_picmenu_next.__main__ import filter_unsupported_adapters
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(
        name="Adapter Plugin",
        supported_adapters={
            "~satori",
            "nonebot.adapters.satori",
            "nonebot.adapters.satori.adapter:Adapter",
        },
    )
    adapter = SatoriAdapter(get_driver())
    result = filter_unsupported_adapters([info], adapter)

    assert result[0] is info


def test_filter_unsupported_adapters_hides_empty_supported_adapters(
    picmenu_plugin: object,  # noqa: ARG001
) -> None:
    from nonebot import get_driver
    from nonebot_plugin_picmenu_next.__main__ import filter_unsupported_adapters
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(name="Adapter Plugin", supported_adapters=set())

    result = filter_unsupported_adapters([info], SatoriAdapter(get_driver()))

    assert result[0] is not info
    assert result[0].pmn.hidden is True


def test_filter_unsupported_adapters_skips_import_when_prefix_mismatch(
    picmenu_plugin: object,  # noqa: ARG001
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    from nonebot import get_driver
    from nonebot_plugin_picmenu_next import __main__
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    info = PMNPluginInfo(
        name="Adapter Plugin",
        supported_adapters={"tests.missing_adapter:Adapter"},
    )

    def fail_resolve(*_args: object, **_kwargs: object) -> object:
        raise AssertionError

    monkeypatch.setattr(__main__, "resolve_dot_notation", fail_resolve)
    result = __main__.filter_unsupported_adapters([info], SatoriAdapter(get_driver()))

    assert result[0] is not info
    assert result[0].pmn.hidden is True

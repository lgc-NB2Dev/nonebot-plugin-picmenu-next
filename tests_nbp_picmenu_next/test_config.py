"""Tests for plugin configuration."""


def test_global_alconna_help_interception_is_opt_in(
    picmenu_plugin: object,
) -> None:
    """ADR-0012 leaves global Alconna Help interception disabled unless configured."""
    from cookit.pyd import type_validate_python
    from nonebot_plugin_picmenu_next.config import ConfigModel

    assert ConfigModel().alconna_global_ext is False
    assert type_validate_python(
        ConfigModel,
        {"pmn_alconna_global_ext": True},
    ).alconna_global_ext

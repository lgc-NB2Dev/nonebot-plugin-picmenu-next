# ruff: noqa: E402

from nonebot.plugin import PluginMetadata, inherit_supported_adapters, require

require("nonebot_plugin_alconna")

from . import __main__ as __main__
from .config import ConfigModel

__version__ = "0.1.0"
__plugin_meta__ = PluginMetadata(
    name="nonebot-plugin-example",
    description="插件模板",
    usage="这是一个一个一个插件模板",
    type="application",
    homepage="https://github.com/lgc-NB2Dev/nonebot-plugin-example",
    config=ConfigModel,
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
    extra={"License": "MIT", "Author": "LgCookie"},
)

# ruff: noqa: E402

from nonebot import get_driver
from nonebot.plugin import PluginMetadata, inherit_supported_adapters, require

require("nonebot_plugin_alconna")
require("nonebot_plugin_waiter")
require("nonebot_plugin_htmlrender")

from . import __main__ as __main__
from .config import ConfigModel
from .data_source import refresh_infos
from .templates import load_builtin_templates

__version__ = "0.1.0.dev1"
__plugin_meta__ = PluginMetadata(
    name="PicMenu Next",
    description="新一代的图片帮助插件",
    usage="发送“帮助”查看所有所有插件功能",
    type="application",
    homepage="https://github.com/lgc-NB2Dev/nonebot-plugin-picmenu-next",
    config=ConfigModel,
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_alconna",
        "nonebot_plugin_waiter",
    ),
    extra={"License": "MIT", "Author": "LgCookie"},
)

load_builtin_templates()

driver = get_driver()


@driver.on_startup
async def _():
    await refresh_infos()

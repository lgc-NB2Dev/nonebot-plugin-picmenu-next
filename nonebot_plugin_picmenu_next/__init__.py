# ruff: noqa: E402

from nonebot.plugin import PluginMetadata, inherit_supported_adapters, require

require("nonebot_plugin_alconna")
require("nonebot_plugin_waiter")
require("nonebot_plugin_htmlrender")

from . import __main__ as __main__
from .config import ConfigModel

__version__ = "0.1.0"
__plugin_meta__ = PluginMetadata(
    name="PicMenuNext",
    description="新一代的图片菜单插件",
    usage="发送“菜单”查看所有所有插件功能",
    type="application",
    homepage="https://github.com/lgc-NB2Dev/nonebot-plugin-picmenu-next",
    config=ConfigModel,
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_alconna",
        "nonebot_plugin_waiter",
    ),
    extra={"License": "MIT", "Author": "student_2333"},
)

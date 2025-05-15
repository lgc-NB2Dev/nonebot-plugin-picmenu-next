from collections.abc import Iterable
from typing import Callable, Optional, TypeVar, overload

from arclet.alconna import Alconna, Arg, Args, CommandMeta, Option, store_true
from nonebot_plugin_alconna import Query, on_alconna
from thefuzz import process

from .data_source import get_resolved_infos
from .templates import index_templates

alc = Alconna(
    "help",
    Args(
        Arg("plugin?", notice="插件序号或名称"),
        Arg("function?", notice="插件功能序号或名称"),
    ),
    Option(
        "-H",
        alias=["--hidden"],
        action=store_true,
        help_text="显示隐藏的插件",
    ),
    meta=CommandMeta(
        description="新一代的图片帮助插件",
        author="LgCookie",
    ),
)
m_cls = on_alconna(
    alc,
    aliases={"帮助", "菜单"},
    skip_for_unmatch=False,
    auto_send_output=True,
    use_cmd_start=True,
)

T = TypeVar("T")
S = TypeVar("S")


@m_cls.handle()
async def _(
    q_plugin: Query[Optional[str]] = Query("~plugin", None),
    q_function: Query[Optional[str]] = Query("~function", None),
    q_hidden: Query[bool] = Query("~hidden", default=False),
):
    infos = await get_resolved_infos()
    if not q_hidden.result:
        infos = [x for x in infos if not x.pmn.hidden]

    if q_function.result:
        pass

    await (await index_templates.data["default"](infos)).finish()

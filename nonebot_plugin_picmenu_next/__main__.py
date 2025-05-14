from cookit.nonebot import CommandArgPlaintext
from nonebot import on_command

from .data_source import get_resolved_infos
from .templates import index_template

m_cls = on_command("help")


@m_cls.handle()
async def _(arg: str = CommandArgPlaintext()):
    show_hidden = "-H" in arg
    infos = await get_resolved_infos()
    if not show_hidden:
        infos = [x for x in infos if not x.pmn.hidden]
    await (await index_template.data["default"](infos)).finish()

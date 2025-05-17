from collections.abc import Sequence
from pathlib import Path
from typing import Optional, TypeVar

from arclet.alconna import Alconna, Arg, Args, CommandMeta, Option, store_true
from loguru import logger
from nonebot.adapters import Bot as BaseBot, Event as BaseEvent
from nonebot.permission import SUPERUSER
from nonebot_plugin_alconna import Query, on_alconna
from nonebot_plugin_alconna.uniseg import UniMessage
from thefuzz import process

from .config import config
from .data_source import get_infos
from .data_source.mixin import resolve_detail_mixin, resolve_main_mixin
from .data_source.models import PinyinChunkSequence, PMDataItem, PMNPluginInfo
from .templates import detail_templates, func_detail_templates, index_templates

RES_DIR = Path(__file__).parent / "res"
TIP_IMG_PATH = RES_DIR / "gan_shen_me.jpg"

alc = Alconna(
    "help",
    Args(
        Arg("plugin?", str, notice="插件序号或名称"),
        Arg("function?", str, notice="插件功能序号或名称"),
    ),
    Option(
        "-H|--show-hidden",
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


def get_name_similarities(
    query: str,
    query_pinyin: str,
    choices: list[str],
    choices_pinyin: list[str],
    raw_weight: float = 0.6,
    pinyin_weight: float = 0.4,
) -> list[float]:
    raw_scores = [x[1] for x in process.extractWithoutOrder(query, choices)]
    pinyin_scores = [
        x[1] for x in process.extractWithoutOrder(query_pinyin, choices_pinyin)
    ]
    similarities = [
        raw_weight * raw + pinyin_weight * pinyin
        for raw, pinyin in zip(raw_scores, pinyin_scores)
    ]
    logger.opt(lazy=True).debug(
        "Query: {}, similarities:\n{}",
        lambda: f"{query} ({query_pinyin})",
        lambda: ";\n".join(
            (
                f"{choices[i]} ({choices_pinyin[i]})"
                f": ({raw} * {raw_weight}) + ({pin} * {pinyin_weight}) = {sim}"
            )
            for i, (raw, pin, sim) in sorted(
                enumerate(zip(raw_scores, pinyin_scores, similarities)),
                key=lambda x: x[1],
                reverse=True,
            )
        ),
    )
    return similarities


T = TypeVar("T")


def handle_query_index(query: str, infos: Sequence[T]) -> Optional[tuple[int, T]]:
    if query.isdigit() and query.strip("0"):
        return (
            ((i := qn - 1), infos[i])
            if (1 <= (qn := int(query)) <= len(infos))
            else None
        )
    return None


async def query_plugin(
    infos: list[PMNPluginInfo],
    query: str,
    score_cutoff: float = 60,
) -> Optional[tuple[int, PMNPluginInfo]]:
    if r := handle_query_index(query, infos):
        return r

    choices: list[str] = []
    choices_pinyin: list[str] = []
    for info in infos:
        choices.append(info.casefold_name)
        choices_pinyin.append(info.name_pinyin.casefold_str)

    similarities = get_name_similarities(
        query.casefold(),
        PinyinChunkSequence.from_raw(query).casefold_str,
        choices,
        choices_pinyin,
    )
    i, s = max(enumerate(similarities), key=lambda x: x[1])
    if s >= score_cutoff:
        return i, infos[i]
    return None


async def query_func_detail(
    pm_data: list[PMDataItem],
    query: str,
    score_cutoff: float = 60,
) -> Optional[tuple[int, PMDataItem]]:
    if r := handle_query_index(query, pm_data):
        return r

    choices: list[str] = []
    choices_pinyin: list[str] = []
    for data in pm_data:
        choices.append(data.casefold_func)
        choices_pinyin.append(data.func_pinyin.casefold_str)

    similarities = get_name_similarities(
        query.casefold(),
        PinyinChunkSequence.from_raw(query).casefold_str,
        choices,
        choices_pinyin,
    )
    i, s = max(enumerate(similarities), key=lambda x: x[1])
    if s >= score_cutoff:
        return i, pm_data[i]
    return None


@m_cls.handle()
async def _(
    bot: BaseBot,
    ev: BaseEvent,
    q_plugin: Query[Optional[str]] = Query("~plugin", None),
    q_function: Query[Optional[str]] = Query("~function", None),
    q_show_hidden: Query[bool] = Query("~show-hidden.value", default=False),
):
    show_hidden = q_show_hidden.result
    if (
        show_hidden
        and config.only_superuser_see_hidden
        and (not await SUPERUSER(bot, ev))
    ):
        await (
            UniMessage.image(raw=TIP_IMG_PATH.read_bytes())
            .text("别想看咱藏起来的东西！")
            .finish(reply_to=True)
        )

    infos = await resolve_main_mixin(get_infos())
    if not show_hidden:
        infos = [x for x in infos if not x.pmn.hidden]

    if not q_plugin.result:
        m = await index_templates.get()(infos, show_hidden)
        await m.finish()

    r = await query_plugin(infos, q_plugin.result)
    if not r:
        await UniMessage.text("好像没有找到对应插件呢……").finish(reply_to=True)
    info_index, info = r
    if not q_function.result:
        m = await detail_templates.get(
            info.pmn.template,
        )(info, info_index, show_hidden)
        await m.finish()

    info = await resolve_detail_mixin(info)
    pm_data = info.pm_data
    if pm_data and (not show_hidden):
        pm_data = [x for x in pm_data if not x.hidden]

    if not pm_data:
        await UniMessage.text(
            f"插件 `{info.name}` 没有详细功能介绍哦",
        ).finish(reply_to=True)

    r = await query_func_detail(pm_data, q_function.result)
    if not r:
        await UniMessage.text(
            f"好像没有找到插件 `{info.name}` 的对应功能呢……",
        ).finish(reply_to=True)
    func_index, func = r
    m = await func_detail_templates.get(
        func.template,
    )(info, info_index, func, func_index, show_hidden)
    await m.finish()

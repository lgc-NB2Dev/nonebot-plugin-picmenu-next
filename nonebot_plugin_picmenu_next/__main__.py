from collections.abc import Sequence
from contextlib import suppress
from typing import Optional, TypeVar

from arclet.alconna import Alconna, Arg, Args, CommandMeta, Option, store_true
from loguru import logger
from nonebot_plugin_alconna import Query, on_alconna
from nonebot_plugin_alconna.uniseg import UniMessage
from thefuzz import process

from .data_source import (
    PMDataItem,
    PMNPluginInfo,
    get_resolved_infos,
    transform_to_pinyin,
)
from .templates import detail_templates, func_detail_templates, index_templates

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
    similarities: list[float] = []
    raw_iter = process.extractWithoutOrder(query, choices)
    pinyin_iter = process.extractWithoutOrder(query_pinyin, choices_pinyin)
    with suppress(StopIteration):
        while True:
            raw_score = next(raw_iter)[1]
            pinyin_score = next(pinyin_iter)[1]
            similarities.append(raw_weight * raw_score + pinyin_weight * pinyin_score)
    logger.opt(lazy=True).debug(
        "Query: {}, similarities: {}",
        lambda: query,
        lambda: "; ".join(
            f"{choices[i]}: {s}"
            for i, s in sorted(
                enumerate(similarities),
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
        choices.append(info.name.casefold())
        choices_pinyin.append(info.name_pinyin.casefold())

    similarities = get_name_similarities(
        query.casefold(),
        transform_to_pinyin(query).casefold(),
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
        choices.append(data.func.casefold())
        choices_pinyin.append(data.func_pinyin.casefold())

    similarities = get_name_similarities(
        query.casefold(),
        transform_to_pinyin(query).casefold(),
        choices,
        choices_pinyin,
    )
    i, s = max(enumerate(similarities), key=lambda x: x[1])
    if s >= score_cutoff:
        return i, pm_data[i]
    return None


@m_cls.handle()
async def _(
    q_plugin: Query[Optional[str]] = Query("~plugin", None),
    q_function: Query[Optional[str]] = Query("~function", None),
    q_show_hidden: Query[bool] = Query("~show-hidden.value", default=False),
):
    infos = await get_resolved_infos()
    if not q_show_hidden.result:
        infos = [x for x in infos if not x.pmn_v.hidden]

    if not q_plugin.result:
        m = await index_templates.get()(infos)
        await m.finish()

    r = await query_plugin(infos, q_plugin.result)
    if not r:
        await UniMessage.text("好像没有找到对应插件呢……").finish(reply_to=True)
    info_index, info = r
    if not q_function.result:
        m = await detail_templates.get(info.pmn.template)(info, info_index)
        await m.finish()

    if not info.pm_data:
        await UniMessage.text(
            f"插件 `{info.name}` 没有详细功能介绍哦",
        ).finish(reply_to=True)

    if (not (plugin := info.plugin)) or (
        not (pm_data := await info.resolve_pm_data(plugin))
    ):
        await UniMessage.text("啊哦，遇到了意外情况……").finish(reply_to=True)

    if not q_show_hidden.result:
        pm_data = [x for x in pm_data if not x.hidden]
    r = await query_func_detail(pm_data, q_function.result)
    if not r:
        await UniMessage.text(
            f"好像没有找到插件 `{info.name}` 的对应功能呢……",
        ).finish(reply_to=True)
    func_index, func = r
    m = await func_detail_templates.get(
        func.template,
    )(info, info_index, func, func_index)
    await m.finish()

from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
from typing import TypeVar, cast, overload
from typing_extensions import override

from arclet.alconna import (
    Alconna,
    Arg,
    Args,
    CommandMeta,
    Option,
    TextFormatter,
    store_true,
)
from cookit.pyd import model_copy
from loguru import logger
from nonebot.adapters import Adapter as BaseAdapter, Bot as BaseBot, Event as BaseEvent
from nonebot.permission import SUPERUSER
from nonebot.utils import resolve_dot_notation
from nonebot_plugin_alconna import Extension, Query, add_global_extension, on_alconna
from nonebot_plugin_alconna.extension import OutputType
from nonebot_plugin_alconna.uniseg import UniMessage
from thefuzz import process

from .config import config
from .data_source import get_infos
from .data_source.alconna import PMNMarkdownTextFormatter, get_alconna_plugin_id
from .data_source.mixin import resolve_detail_mixin, resolve_main_mixin
from .data_source.models import PinyinChunkSequence, PMDataItem, PMNPluginInfo
from .templates import detail_templates, func_detail_templates, index_templates

RES_DIR = Path(__file__).parent / "res"
TIP_IMG_PATH = RES_DIR / "gan_shen_me.jpg"

T = TypeVar("T")


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
        author="LgCuwukii",
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


def handle_query_index(query: str, infos: Sequence[T]) -> tuple[int, T] | None:
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
) -> tuple[int, PMNPluginInfo] | None:
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
) -> tuple[int, PMDataItem] | None:
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


def filter_hidden_functions(info: PMNPluginInfo) -> PMNPluginInfo:
    if not info.pm_data:
        return info
    return model_copy(
        info, update={"pm_data": [x for x in info.pm_data if not x.hidden]}
    )


def is_plugin_supported_adapter(info: PMNPluginInfo, adapter: BaseAdapter) -> bool:
    plugin = info.plugin
    if (not plugin) or (not plugin.metadata):
        return True
    if (supported_adapters := plugin.metadata.supported_adapters) is None:
        return True

    current_module = type(adapter).__module__
    for supported_adapter in supported_adapters:
        module, _, _ = supported_adapter.partition(":")
        if module.startswith("~"):
            module = f"nonebot.adapters.{module[1:]}"
        if current_module != module and not current_module.startswith(f"{module}."):
            continue

        with suppress(ModuleNotFoundError, ImportError, AttributeError):
            adapter_class = resolve_dot_notation(
                supported_adapter,
                "Adapter",
                "nonebot.adapters.",
            )
            if isinstance(adapter_class, type) and isinstance(adapter, adapter_class):
                return True
    return False


def filter_unsupported_adapters(
    infos: list[PMNPluginInfo],
    adapter: BaseAdapter,
) -> list[PMNPluginInfo]:
    return [
        info
        if is_plugin_supported_adapter(info, adapter)
        else model_copy(
            info, update={"pmn": model_copy(info.pmn, update={"hidden": True})}
        )
        for info in infos
    ]


@overload
async def render_menu(
    bot: BaseBot,
    *,
    q_plugin: str | None = None,
    q_function: str | None = None,
    show_hidden: bool = False,
) -> tuple[UniMessage | None, PMNPluginInfo | None, PMDataItem | None]: ...


@overload
async def render_menu(
    bot: BaseBot,
    *,
    plugin_id: str | None = None,
    alc_cmd_id: str | None = None,
    alc_detail_des: str | None = None,
    show_hidden: bool = False,
) -> tuple[UniMessage | None, PMNPluginInfo | None, PMDataItem | None]: ...


async def render_menu(
    bot: BaseBot,
    q_plugin: str | None = None,
    q_function: str | None = None,
    plugin_id: str | None = None,
    alc_cmd_id: str | None = None,
    alc_detail_des: str | None = None,
    show_hidden: bool = False,
) -> tuple[UniMessage | None, PMNPluginInfo | None, PMDataItem | None]:
    infos = filter_unsupported_adapters(get_infos(), bot.adapter)
    infos = await resolve_main_mixin(infos)
    if not show_hidden:
        infos = [x for x in infos if not x.pmn.hidden]
    if not infos:
        return None, None, None

    if plugin_id:
        r = next(
            ((i, x) for i, x in enumerate(infos) if x.plugin_id == plugin_id), None
        )
    elif q_plugin:
        r = await query_plugin(infos, q_plugin)
    else:
        return await index_templates.get()(infos, show_hidden), None, None

    if not r:
        return None, None, None

    info_index, info = r
    if not show_hidden:
        info = filter_hidden_functions(info)
    info = await resolve_detail_mixin(info)

    if (not q_function) and (not alc_cmd_id):
        return (
            await detail_templates.get(
                info.pmn.template,
            )(info, info_index, show_hidden),
            info,
            None,
        )

    pm_data = info.pm_data
    if not pm_data:
        return None, info, None

    if alc_cmd_id:
        r = next(
            ((i, x) for i, x in enumerate(pm_data) if x.alc_cmd_id == alc_cmd_id), None
        )
    else:
        assert q_function is not None
        r = await query_func_detail(pm_data, q_function)

    if not r:
        return None, info, None

    func_index, func = r
    if alc_detail_des is not None:
        func = model_copy(func, update={"detail_des": alc_detail_des})
    return (
        await func_detail_templates.get(
            func.template,
        )(info, info_index, func, func_index, show_hidden),
        info,
        func,
    )


@m_cls.handle()
async def _(
    bot: BaseBot,
    ev: BaseEvent,
    q_plugin: Query[str | None] = Query("~plugin", None),
    q_function: Query[str | None] = Query("~function", None),
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
            .text("不是主人不给看")
            .finish(reply_to=True)
        )

    msg, info, func = await render_menu(
        bot,
        q_plugin=(qp := q_plugin.result),
        q_function=(qf := q_function.result),
        show_hidden=show_hidden,
    )
    if msg:
        await msg.finish()

    if (not qp) and (not qf):
        await UniMessage.text(
            "当前貌似没有任何可用的插件信息呢……",
        ).finish(reply_to=True)

    if not info:
        await UniMessage.text("好像没有找到对应插件呢……").finish(reply_to=True)

    if (not func) and info.pm_data and qf:
        await UniMessage.text(
            f"好像没有找到插件 `{info.name}` 的对应功能呢……",
        ).finish(reply_to=True)

    await UniMessage.text(
        f"插件 `{info.name}` 没有详细功能介绍哦",
    ).finish(reply_to=True)


# Alconna formats `-h/--help` before `output_converter`, and that converter does
# not receive the current Arparma. To avoid reparsing help text, replace the
# command formatter with PicMenu's markdown formatter before parsing. `post_init`
# is the earliest chance; if plugin ownership/registry data is not ready there,
# retry in `validate`, which runs before help parsing.
class PMNHelpExtension(Extension):
    command: "Alconna | None" = None
    _formatter_checked: bool = False

    @property
    def priority(self) -> int:
        return 8

    @property
    def id(self) -> str:
        return "picmenu-next-help"

    def _ensure_markdown_formatter(self) -> None:
        if self._formatter_checked or not self.command:
            return
        plugin_id = get_alconna_plugin_id(self.command)
        if not plugin_id:
            return
        info = next((x for x in get_infos() if x.plugin_id == plugin_id), None)
        if info is None:
            return
        self._formatter_checked = True
        if (nm := (not info.pmn.markdown)) or (
            type(self.command.formatter) is not TextFormatter
        ):
            logger.debug(
                f"Markdown formatter set skipped for command {self.command.path}"
                f" ({'Does not support markdown' if nm else 'Already has custom formatter'})",
            )
            return
        self.command.formatter = PMNMarkdownTextFormatter().add(self.command)
        logger.debug(f"Markdown formatter applied to command {self.command.path}")

    @override
    def validate(self, bot: BaseBot, event: BaseEvent) -> bool:
        self._ensure_markdown_formatter()
        return super().validate(bot, event)

    @override
    async def output_converter(
        self,
        output_type: OutputType,
        content: str,
    ) -> UniMessage:
        if (
            output_type == "help"
            and self.command
            and (plugin_id := get_alconna_plugin_id(self.command))
        ):
            bot = cast("BaseBot", await self.inject(("bot", BaseBot)))
            msg, _, _ = await render_menu(
                bot,
                plugin_id=plugin_id,
                alc_cmd_id=self.command.path,
                alc_detail_des=content,
            )
            if msg:
                return msg
        return await super().output_converter(output_type, content)

    @override
    def post_init(self, alc: "Alconna") -> None:
        self.command = alc
        self._ensure_markdown_formatter()


if config.alconna_global_ext:
    add_global_extension(PMNHelpExtension)

from collections import defaultdict
from collections.abc import Coroutine, Sequence
from dataclasses import dataclass
from typing import Any, Callable, Generic, Optional, TypeVar
from typing_extensions import Concatenate, ParamSpec, TypeAlias

from cookit import DecoListCollector
from cookit.loguru import warning_suppress
from nonebot.matcher import MatcherSource
from nonebot.plugin.on import get_matcher_source

from .models import PMNPluginInfo

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

P = ParamSpec("P")

Co: TypeAlias = Coroutine[Any, Any, T]
MixinFunc: TypeAlias = Callable[
    Concatenate[
        Callable[P, T],
        P,
    ],
    T,
]

PluginCollectMixinNext: TypeAlias = Callable[
    [list[PMNPluginInfo]],
    Co[list[PMNPluginInfo]],
]
PluginCollectMixin: TypeAlias = MixinFunc[
    [list[PMNPluginInfo]],
    Co[list[PMNPluginInfo]],
]

SelfMixinNext: TypeAlias = Callable[
    [PMNPluginInfo],
    Co[PMNPluginInfo],
]
SelfMixin: TypeAlias = MixinFunc[
    [PMNPluginInfo],
    Co[PMNPluginInfo],
]

PluginMixinNext: TypeAlias = Callable[
    [list[PMNPluginInfo]],
    Co[list[PMNPluginInfo]],
]
PluginMixin: TypeAlias = MixinFunc[
    [list[PMNPluginInfo]],
    Co[list[PMNPluginInfo]],
]

PluginDetailMixinNext: TypeAlias = Callable[
    [PMNPluginInfo],
    Co[PMNPluginInfo],
]
PluginDetailMixin: TypeAlias = MixinFunc[
    [PMNPluginInfo],
    Co[PMNPluginInfo],
]


@dataclass
class MixinInfo(Generic[T]):
    func: T
    priority: int
    source: Optional[MatcherSource]


class MixinCollector(DecoListCollector[MixinInfo[T]]):
    def __call__(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        priority: int = 5,
        _depth: int = 0,
        _matcher_source: Optional[MatcherSource] = None,
    ):
        def deco(func: T) -> T:
            self.data.append(
                MixinInfo(
                    func=func,
                    priority=priority,
                    source=get_matcher_source(_depth + 1),
                ),
            )
            self.data.sort(key=lambda x: x.priority)
            return func

        return deco


class SelfMixinCollector(defaultdict[str, MixinCollector[T]]):
    def __init__(self) -> None:
        super().__init__(MixinCollector)

    def __call__(
        self,
        priority: int = 1,
        _depth: int = 0,
        _matcher_source: Optional[MatcherSource] = None,
    ):
        def deco(f: T) -> T:
            s = _matcher_source or get_matcher_source()
            if (not s) or not (pid := s.plugin_id):
                raise ValueError("Self plugin not found")
            self[pid](priority, _depth + 1, s)(f)
            return f

        return deco


plugin_collect_mixins: MixinCollector[PluginCollectMixin] = MixinCollector()

self_mixins: SelfMixinCollector[SelfMixin] = SelfMixinCollector()
self_detail_mixins: SelfMixinCollector[PluginDetailMixin] = SelfMixinCollector()

plugin_mixins = MixinCollector[PluginMixin]()
plugin_detail_mixins = MixinCollector[PluginDetailMixin]()


def format_source_warn_msg(info: MixinInfo) -> str:
    if (not (s := info.source)) or not s.plugin_id:
        return "Failed to run mixin from unknown source"
    return (
        f"Failed to run mixin from plugin {s.plugin_id}"
        f" at module {s.module_name or 'unknown'}, line {s.lineno or 'unknown'}"
    )


def chain_mixins(
    mixins: Sequence[MixinInfo[MixinFunc[P, Co[T]]]],
    final_mixin: Callable[P, Co[T]],
) -> Callable[P, Co[T]]:
    """
    将一系列中间件函数链接起来，形成一个调用链。

    Args:
        mixins: 中间件函数列表，每个函数接收下一个调用函数和其他参数。
        final_mixin: 最终执行的函数，只接收其他参数。

    Returns:
        链接后的函数，接收与 final_mixin 相同的参数。
    """

    # 如果没有中间件，直接返回最终函数
    if not mixins:
        return final_mixin

    # 从后向前构建调用链
    chain = final_mixin

    # 使用函数工厂避免闭包中的变量绑定问题
    def create_wrapper(
        current_mixin: MixinInfo[MixinFunc[P, Co[T]]],
        next_chain: Callable[P, Co[T]],
    ) -> Callable[P, Co[T]]:
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
            with warning_suppress(lambda _: format_source_warn_msg(current_mixin)):
                return await current_mixin.func(next_chain, *args, **kwargs)
            return await next_chain(*args, **kwargs)

        return wrapped

    # 从后向前应用每个中间件
    for mixin in reversed(mixins):
        chain = create_wrapper(mixin, chain)

    return chain


async def resolve_main_mixin(infos: list[PMNPluginInfo]):
    if not infos:
        return infos

    infos = infos.copy()

    if plugin_mixins.data:

        async def last_external_mixin(infos: list[PMNPluginInfo]):
            return infos

        external_mixin_chain = chain_mixins(
            plugin_mixins.data,
            last_external_mixin,
        )
        infos = await external_mixin_chain(infos)

    for i in range(len(infos)):
        x = infos[i]
        if (not x.plugin_id) or (x.plugin_id not in self_mixins):
            continue

        async def last_mixin(info: PMNPluginInfo):
            return info

        self_mixin_chain = chain_mixins(
            self_mixins[x.plugin_id].data,
            last_mixin,
        )
        infos[i] = await self_mixin_chain(x)

    return infos


async def resolve_detail_mixin(info: PMNPluginInfo):
    async def last_mixin(info: PMNPluginInfo):
        return info

    if plugin_detail_mixins.data:
        mixin_chain = chain_mixins(
            plugin_detail_mixins.data,
            last_mixin,
        )
        info = await mixin_chain(info)

    if info.plugin_id and info.plugin_id in self_detail_mixins:
        mixin_chain = chain_mixins(
            self_detail_mixins[info.plugin_id].data,
            last_mixin,
        )
        info = await mixin_chain(info)

    return info

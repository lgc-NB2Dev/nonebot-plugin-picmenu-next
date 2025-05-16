import asyncio

from nonebot import get_loaded_plugins as _get_loaded_plugins

from .collect import collect_plugin_infos as _collect_plugin_infos
from .models import (
    PMNPluginInfo as _PMNPluginInfo,
    PMNPluginInfoRaw as _PMNPluginInfoRaw,
)

_infos: list[_PMNPluginInfoRaw] = []


def get_infos() -> list[_PMNPluginInfoRaw]:
    return _infos


async def refresh_infos() -> list[_PMNPluginInfoRaw]:
    global _infos
    _infos = await _collect_plugin_infos(_get_loaded_plugins())
    return _infos


async def get_resolved_infos() -> list[_PMNPluginInfo]:
    return await asyncio.gather(
        *(_PMNPluginInfo.resolve(x, p) for x in _infos if (p := x.plugin)),
    )

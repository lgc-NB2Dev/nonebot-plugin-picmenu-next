import asyncio

from cookit.loguru import warning_suppress as _warning_suppress
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
    async def _resolve(p: _PMNPluginInfoRaw):
        with _warning_suppress(f"Failed to resolve plugin info of {p.name}"):
            return await _PMNPluginInfo.resolve(p)

    r = await asyncio.gather(*(_resolve(x) for x in _infos))
    return [v for v in r if v]

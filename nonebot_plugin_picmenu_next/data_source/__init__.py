from nonebot import get_loaded_plugins as _get_loaded_plugins

from .collect import collect_plugin_infos as _collect_plugin_infos
from .models import PMNPluginInfo as _PMNPluginInfoRaw

_infos: list[_PMNPluginInfoRaw] = []


def get_infos() -> list[_PMNPluginInfoRaw]:
    return _infos


async def refresh_infos() -> list[_PMNPluginInfoRaw]:
    global _infos
    _infos = await _collect_plugin_infos(_get_loaded_plugins())
    return _infos

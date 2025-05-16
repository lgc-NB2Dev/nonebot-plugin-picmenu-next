import asyncio
from collections.abc import Iterable
from importlib.metadata import Distribution, distribution
from typing import Literal, Optional, Union

from cookit.loguru import warning_suppress
from cookit.pyd import type_validate_python
from nonebot import logger
from nonebot.plugin import Plugin

from ..utils import normalize_plugin_name
from .models import PMNDataRaw, PMNPluginExtra, PMNPluginInfoRaw


def normalize_metadata_user(info: str, allow_multi: bool = False) -> str:
    infos = info.split(",")
    if not allow_multi:
        infos = infos[:1]
    return " & ".join(x.split("<")[0].strip().strip("'\"") for x in infos)


async def get_info_from_plugin(plugin: Plugin) -> PMNPluginInfoRaw:
    meta = plugin.metadata
    extra: Optional[PMNPluginExtra] = None
    if meta:
        with warning_suppress(f"Failed to parse plugin metadata of {plugin.id_}"):
            extra = type_validate_python(PMNPluginExtra, meta.extra)

    name = normalize_plugin_name(meta.name if meta else plugin.id_)

    _dist: Union[Distribution, None, Literal[False]] = False

    def get_dist() -> Optional[Distribution]:
        nonlocal _dist
        if _dist is not False:
            return _dist

        _dist = None
        module = plugin.module_name
        while True:
            with warning_suppress(
                f"Failed to get info of package {module}",
                level="DEBUG",
                debug_stack=False,
            ):
                _dist = distribution(module)
                return _dist
            if "." not in module:
                return None
            module = module.rsplit(".", 1)[0]

    ver = extra.version if extra else None
    if not ver:
        ver = getattr(plugin, "__version__", None)
    if not ver and (dist := get_dist()):
        ver = dist.version

    author = (
        (" & ".join(extra.author) if isinstance(extra.author, list) else extra.author)
        if extra
        else None
    )
    if not author and (dist := get_dist()):
        if author := dist.metadata.get("Author") or dist.metadata.get("Maintainer"):
            author = normalize_metadata_user(author)
        elif author := dist.metadata.get("Author-Email") or dist.metadata.get(
            "Maintainer-Email",
        ):
            author = normalize_metadata_user(author, allow_multi=True)

    description = (
        meta.description
        if meta
        else (dist.metadata.get("Summary") if (dist := get_dist()) else None)
    )

    pmn = (extra.pmn if extra else None) or PMNDataRaw()
    if ("hidden" not in pmn.model_fields_set) and meta and meta.type == "library":
        pmn = PMNDataRaw(hidden=True)

    logger.debug(f"Completed to get info of plugin {plugin.id_}")
    obj = PMNPluginInfoRaw(
        name=name,
        author=author,
        version=ver,
        description=description,
        usage=meta.usage if meta else None,
        pm_data=extra.menu_data if extra else None,
        pmn=pmn,
    )
    obj.plugin = plugin
    return obj


async def collect_plugin_infos(plugins: Iterable[Plugin]):
    async def _get(p: Plugin):
        with warning_suppress(f"Failed to get plugin info of {p.id_}"):
            return await get_info_from_plugin(p)

    infos = await asyncio.gather(
        *(_get(plugin) for plugin in plugins),
    )
    infos = [x for x in infos if x]
    logger.success(f"Collected {len(infos)} plugin infos")
    infos.sort(key=lambda x: x.name_pinyin)
    return infos

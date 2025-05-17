import asyncio
import importlib
from collections.abc import Iterable
from contextlib import suppress
from functools import lru_cache
from importlib.metadata import Distribution, PackageNotFoundError, distribution
from typing import Optional

from cookit.loguru import warning_suppress
from cookit.pyd import type_validate_python
from nonebot import logger
from nonebot.plugin import Plugin

from ..utils import normalize_plugin_name
from .mixin import chain_mixins, plugin_collect_mixins
from .models import PMNData, PMNPluginExtra, PMNPluginInfo


def normalize_metadata_user(info: str, allow_multi: bool = False) -> str:
    infos = info.split(",")
    if not allow_multi:
        infos = infos[:1]
    return " & ".join(x.split("<")[0].strip().strip("'\"") for x in infos)


@lru_cache
def get_dist(module_name: str) -> Optional[Distribution]:
    with warning_suppress(f"Unexpected error happened when getting info of package {module_name}"),\
        suppress(PackageNotFoundError):  # fmt: skip
        return distribution(module_name)
    if "." not in module_name:
        return None
    module_name = module_name.rsplit(".", 1)[0]
    return get_dist(module_name)


@lru_cache
def get_version_attr(module_name: str) -> Optional[str]:
    with warning_suppress(f"Unexpected error happened when importing {module_name}"),\
        suppress(ImportError):  # fmt: skip
        m = importlib.import_module(module_name)
        if ver := getattr(m, "__version__", None):
            return ver
    if "." not in module_name:
        return None
    module_name = module_name.rsplit(".", 1)[0]
    return get_version_attr(module_name)


async def get_info_from_plugin(plugin: Plugin) -> PMNPluginInfo:
    meta = plugin.metadata
    extra: Optional[PMNPluginExtra] = None
    if meta:
        with warning_suppress(f"Failed to parse plugin metadata of {plugin.id_}"):
            extra = type_validate_python(PMNPluginExtra, meta.extra)

    name = normalize_plugin_name(meta.name if meta else plugin.id_)

    ver = extra.version if extra else None
    if not ver:
        ver = get_version_attr(plugin.module_name)
    if not ver and (dist := get_dist(plugin.module_name)):
        ver = dist.version

    author = (
        (" & ".join(extra.author) if isinstance(extra.author, list) else extra.author)
        if extra
        else None
    )
    if not author and (dist := get_dist(plugin.module_name)):
        if author := dist.metadata.get("Author") or dist.metadata.get("Maintainer"):
            author = normalize_metadata_user(author)
        elif author := dist.metadata.get("Author-Email") or dist.metadata.get(
            "Maintainer-Email",
        ):
            author = normalize_metadata_user(author, allow_multi=True)

    description = (
        meta.description
        if meta
        else (
            dist.metadata.get("Summary")
            if (dist := get_dist(plugin.module_name))
            else None
        )
    )

    pmn = (extra.pmn if extra else None) or PMNData()
    if ("hidden" not in pmn.model_fields_set) and meta and meta.type == "library":
        pmn = PMNData(hidden=True)

    logger.debug(f"Completed to get info of plugin {plugin.id_}")
    return PMNPluginInfo(
        plugin_id=plugin.id_,
        name=name,
        author=author,
        version=ver,
        description=description,
        usage=meta.usage if meta else None,
        pm_data=extra.menu_data if extra else None,
        pmn=pmn,
    )


async def collect_plugin_infos(plugins: Iterable[Plugin]):
    async def _get(p: Plugin):
        with warning_suppress(f"Failed to get plugin info of {p.id_}"):
            return await get_info_from_plugin(p)

    infos = await asyncio.gather(
        *(_get(plugin) for plugin in plugins),
    )
    infos = [x for x in infos if x]

    async def final_mixin(infos: list[PMNPluginInfo]):
        return infos

    mixin_chain = chain_mixins(plugin_collect_mixins.data, final_mixin)
    infos = await mixin_chain(infos)

    infos.sort(key=lambda x: x.name_pinyin)
    logger.success(f"Collected {len(infos)} plugin infos")

    get_dist.cache_clear()
    get_version_attr.cache_clear()
    return infos

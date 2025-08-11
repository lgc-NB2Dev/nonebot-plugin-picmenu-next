import asyncio
import importlib
from collections.abc import Generator, Iterable
from contextlib import suppress
from functools import lru_cache
from importlib.metadata import Distribution, PackageNotFoundError, distribution
from pathlib import Path

from cookit.loguru import warning_suppress
from cookit.pyd import type_validate_json, type_validate_python
from nonebot import logger
from nonebot.plugin import Plugin

from ..config import external_infos_dir, pm_menus_dir
from ..utils import normalize_plugin_name
from .mixin import PluginCollectMixinNext, chain_mixins, plugin_collect_mixins
from .models import ExternalPluginInfo, PMNData, PMNPluginExtra, PMNPluginInfo


def normalize_metadata_user(info: str, allow_multi: bool = False) -> str:
    infos = info.split(",")
    if not allow_multi:
        infos = infos[:1]
    return " & ".join(x.split("<")[0].strip().strip("'\"") for x in infos)


@lru_cache
def get_dist(module_name: str) -> Distribution | None:
    with warning_suppress(f"Unexpected error happened when getting info of package {module_name}"),\
        suppress(PackageNotFoundError):  # fmt: skip
        return distribution(module_name)
    if "." not in module_name:
        return None
    module_name = module_name.rsplit(".", 1)[0]
    return get_dist(module_name)


@lru_cache
def get_version_attr(module_name: str) -> str | None:
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
    extra: PMNPluginExtra | None = None
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
        if (("Author" in dist.metadata) and (author := dist.metadata["Author"])) or (
            ("Maintainer" in dist.metadata) and (author := dist.metadata["Maintainer"])
        ):
            author = normalize_metadata_user(author)
        elif (
            ("Author-Email" in dist.metadata)
            and (author := dist.metadata["Author-Email"])
        ) or (
            ("Maintainer-Email" in dist.metadata)
            and (author := dist.metadata["Maintainer-Email"])
        ):
            author = normalize_metadata_user(author, allow_multi=True)

    description = (
        meta.description
        if meta
        else (
            dist.metadata["Summary"]
            if (dist := get_dist(plugin.module_name)) and "Summary" in dist.metadata
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


def scan_path(path: Path, suffixes: Iterable[str] | None = None) -> Generator[Path]:
    for child in path.iterdir():
        if child.is_dir():
            yield from scan_path(child, suffixes)
        elif suffixes and child.suffix in suffixes:
            yield child


async def collect_menus():
    yaml = None

    supported_suffixes = {".json", ".yml", ".yaml", ".toml"}

    def _load_file(path: Path) -> ExternalPluginInfo:
        nonlocal yaml

        if path.suffix == ".json":
            return type_validate_json(ExternalPluginInfo, path.read_text("u8"))

        if path.suffix in {".yml", ".yaml"}:
            if not yaml:
                try:
                    from ruamel.yaml import YAML
                except ImportError as e:
                    raise ImportError(
                        "Missing dependency for parsing yaml files, please install using"
                        " `pip install nonebot-plugin-picmenu-next[yaml]`",
                    ) from e
                yaml = YAML()
            return type_validate_python(
                ExternalPluginInfo,
                yaml.load(path.read_text("u8")),
            )

        if path.suffix == ".toml":
            try:
                import tomllib
            except ImportError:
                try:
                    import tomli as tomllib
                except ImportError as e:
                    raise ImportError(
                        "Missing dependency for parsing toml files, please install using"
                        " `pip install nonebot-plugin-picmenu-next[toml]`",
                    ) from e
            return type_validate_python(
                ExternalPluginInfo,
                tomllib.loads(path.read_text("u8")),
            )

        raise ValueError("Unsupported file type")

    infos: dict[str, ExternalPluginInfo] = {}

    def _load_to_infos(path: Path):
        if path.name in infos:
            logger.warning(
                f"Find file with duplicated name `{path.name}`! Skip loading {{path}}",
            )
            return
        with warning_suppress(f"Failed to load file {path}"):
            infos[path.name] = _load_file(path)

    def _load_all(path: Path):
        for x in scan_path(path, supported_suffixes):
            _load_to_infos(x)

    if pm_menus_dir.exists():
        logger.warning(
            "Old PicMenu menus dir is deprecated"
            ", recommended to migrate to PicMenu Next config dir",
        )
        _load_all(pm_menus_dir)

    _load_all(external_infos_dir)

    return infos


@plugin_collect_mixins(priority=1)
async def load_user_custom_infos_mixin(
    next_mixin: PluginCollectMixinNext,
    infos: list[PMNPluginInfo],
) -> list[PMNPluginInfo]:
    external_infos = await collect_menus()
    if not external_infos:
        return await next_mixin(infos)
    logger.info(f"Collected {len(external_infos)} external infos")

    infos_map = {x.plugin_id: x for x in infos if x.plugin_id}
    for k, v in external_infos.items():
        if k in infos_map:
            logger.debug(f"Found `{k}` in infos, will merge to original")
            v.merge_to(infos_map[k], plugin_id=k, copy=False)
        else:
            logger.debug(f"Not found `{k}` in infos, will add into")
            infos.append(v.to_plugin_info(k))

    return await next_mixin(infos)


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

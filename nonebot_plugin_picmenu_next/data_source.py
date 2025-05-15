import asyncio
import importlib
from asyncio import iscoroutinefunction
from collections.abc import Awaitable, Iterable
from importlib.metadata import Distribution, distribution
from typing import Any, Optional, Union
from typing_extensions import Self
from weakref import ref

import jieba
from cookit.loguru import warning_suppress
from cookit.pyd import model_validator, type_dump_python, type_validate_python
from nonebot import logger
from nonebot.plugin import Plugin, get_loaded_plugins
from pydantic import BaseModel, Field, PrivateAttr
from pypinyin import Style, pinyin


async def call_entrypoint(plugin: Plugin, entrypoint: str) -> Any:
    """`module_name:function_name` string.
    You can Use `~` in module name to replace your plugin module name."""

    module_path, func_name = entrypoint.split(":")
    module_path = module_path.replace("~", plugin.module_name)
    module = importlib.import_module(module_path)
    func = getattr(module, func_name)
    return (await func()) if iscoroutinefunction(func) else func()


async def resolve_func_hidden(plugin: Plugin, entrypoint: str) -> bool:
    """should only be called from event handler,
    so hidden func can get current bot, event, etc."""

    with warning_suppress(
        f"Failed to resole hidden status `{entrypoint}` from plugin {plugin.id_}",
    ):
        return bool(await call_entrypoint(plugin, entrypoint))
    return False


class PMDataItemRaw(BaseModel):
    func: str
    func_pinyin: str
    trigger_method: str
    trigger_condition: str
    brief_des: str
    detail_des: str

    # extension properties
    hidden: Union[bool, str] = Field(default=False, alias="pmn_hidden")
    template: Optional[str] = Field(default=None, alias="pmn_template")

    @model_validator(mode="before")
    def init_func_pinyin(cls, values: Any):  # noqa: N805
        if isinstance(values, BaseModel):
            values = type_dump_python(values, exclude_unset=True)
        if isinstance((func := values.get("func")), str) and (
            not values.get("func_pinyin")
        ):
            values["func_pinyin"] = transform_to_pinyin(func)
        return values


class PMDataItem(PMDataItemRaw):
    pmn_hidden_v: bool = False

    @classmethod
    async def resolve(cls, plugin: Plugin, data: PMDataItemRaw) -> Self:
        data_dict: dict = type_dump_python(data, exclude_unset=True)
        if isinstance((hidden := data_dict.get("pmn_hidden")), str):
            data_dict["pmn_hidden_v"] = await resolve_func_hidden(plugin, hidden)
        return cls(**data_dict)


class PMNDataRaw(BaseModel):
    hidden: Union[bool, str] = False
    markdown: bool = False
    template: Optional[str] = None


class PMNData(PMNDataRaw):
    hidden_v: bool = False

    @classmethod
    async def resolve(cls, plugin: Plugin, data: PMNDataRaw) -> Self:
        data_dict: dict = type_dump_python(data, exclude_unset=True)
        if isinstance((hidden := data_dict.get("hidden")), str):
            data_dict["hidden_v"] = await resolve_func_hidden(plugin, hidden)
        return cls(**data_dict)


class PMNPluginExtra(BaseModel):
    author: Union[str, list[str], None] = None
    version: Optional[str] = None
    menu_data: Optional[list[PMDataItemRaw]] = None
    pmn: Optional[PMNDataRaw] = None

    @model_validator(mode="before")
    def normalize_input(cls, values: dict[str, Any]):  # noqa: N805
        should_normalize_keys = {x for x in values if x.lower() in {"author"}}
        for key in should_normalize_keys:
            value = values[key]
            del values[key]
            values[key.lower()] = value
        return values


class PMNPluginInfoRaw(BaseModel):
    name: str
    name_pinyin: str
    author: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    usage: Optional[str] = None
    pm_data: Optional[list[PMDataItemRaw]] = None
    pmn: PMNDataRaw = PMNDataRaw()

    _resolved_pm_data: Optional[list[PMDataItem]] = PrivateAttr(None)

    @model_validator(mode="before")
    def init_name_pinyin(cls, values: dict[str, Any]):  # noqa: N805
        if isinstance((name := values.get("name")), str) and (
            not values.get("name_pinyin")
        ):
            values["name_pinyin"] = transform_to_pinyin(name)
        return values

    async def resolve_pm_data(self, plugin: Plugin):
        if self._resolved_pm_data is not None:
            return self._resolved_pm_data
        if not self.pm_data:
            return None

        async def _ts(x: PMDataItemRaw):
            with warning_suppress(
                f"Failed to resolve plugin menu item `{x.func}` of {plugin.id_}",
            ):
                return await PMDataItem.resolve(plugin, x)

        self._resolved_pm_data = [
            x for x in await asyncio.gather(*(_ts(x) for x in self.pm_data)) if x
        ]
        return self._resolved_pm_data


class PMNPluginInfo(PMNPluginInfoRaw):
    pmn_v: PMNData = PMNData()

    _plugin: Optional[ref[Plugin]] = PrivateAttr(None)

    @property
    def plugin(self) -> Optional[Plugin]:
        if self._plugin:
            return self._plugin()
        return None

    @plugin.setter
    def plugin(self, plugin: Plugin):
        self._plugin = ref(plugin)

    @classmethod
    async def resolve(cls, plugin: Plugin, data: PMNPluginInfoRaw) -> Self:
        data_dict: dict = type_dump_python(data, exclude_unset=True)
        tasks: list[Awaitable] = []

        if pmn := data_dict.get("pmn"):

            async def _t():
                v = None
                with warning_suppress(
                    f"Failed to resolve PicMenu Next data of {plugin.id_}",
                ):
                    v = await PMNData.resolve(plugin, pmn)
                data_dict["pmn_v"] = v

            tasks.append(_t())

        await asyncio.gather(*tasks)
        ins = cls(**data_dict)
        ins.plugin = plugin
        return ins


def normalize_plugin_name(name: str) -> str:
    if pfx := next(
        (x for x in ("nonebot_plugin_", "nonebot-plugin-") if name.startswith(x)),
        None,
    ):
        name = name[len(pfx) :].replace("_", " ").title()
    return name


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

    name = (
        normalize_plugin_name(meta.name)
        if meta
        else normalize_plugin_name(
            plugin.id_.replace(".", " ").replace(":", " "),
        ).title()
    )

    _dist = ...

    def get_dist() -> Optional[Distribution]:
        nonlocal _dist
        if _dist is ...:
            _dist = None
            with warning_suppress(
                f"Failed to get info of package {plugin.module_name}",
            ):
                _dist = distribution(plugin.module_name)
        return _dist

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
    return PMNPluginInfoRaw(
        name=name,
        name_pinyin="",  # avoid type error
        author=author,
        version=ver,
        description=description,
        usage=meta.usage if meta else None,
        pm_data=extra.menu_data if extra else None,
        pmn=pmn,
    )


class _NotCHNStr(str):  # noqa: SLOT000
    pass


def pinyin_sorter_k(text: str):
    return tuple(
        (
            is_pinyin := not isinstance((x := v[0]), _NotCHNStr),
            x[:-1] if is_pinyin else x,
            int(x[-1]) if is_pinyin else 0,
        )
        for v in pinyin(
            jieba.lcut(text),
            style=Style.TONE3,
            errors=lambda x: _NotCHNStr(x),
            neutral_tone_with_five=True,
        )
    )


async def collect_plugin_infos(plugins: Iterable[Plugin]):
    async def _get(p: Plugin):
        with warning_suppress(f"Failed to get plugin info of {p.id_}"):
            return await get_info_from_plugin(p)

    infos = await asyncio.gather(
        *(_get(plugin) for plugin in plugins),
    )
    infos = [x for x in infos if x]
    logger.success(f"Collected {len(infos)} plugin infos")
    infos.sort(key=lambda x: x.name)
    return infos


def transform_to_pinyin(text: str) -> str:
    return " ".join(
        v[0]
        for v in pinyin(
            jieba.lcut(text),
            style=Style.TONE3,
            neutral_tone_with_five=True,
        )
    )


_infos: list[PMNPluginInfoRaw] = []
_plugin_refs: list[ref[Plugin]] = []


def get_infos() -> list[PMNPluginInfoRaw]:
    return _infos


def get_plugin_refs() -> list[ref[Plugin]]:
    return _plugin_refs


async def refresh_infos() -> list[PMNPluginInfoRaw]:
    global _plugin_refs, _infos
    plugins = get_loaded_plugins()
    _infos = await collect_plugin_infos(plugins)
    _plugin_refs = [ref(plugin) for plugin in plugins]
    return _infos


async def get_resolved_infos() -> list[PMNPluginInfo]:
    return await asyncio.gather(
        *(
            PMNPluginInfo.resolve(p, x)
            for r, x in zip(_plugin_refs, _infos)
            if (p := r())
        ),
    )

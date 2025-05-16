import asyncio
import importlib
import re
from asyncio import iscoroutinefunction
from collections.abc import Awaitable, Iterable, Iterator, Sequence
from functools import cached_property
from importlib.metadata import Distribution, distribution
from typing import Any, NamedTuple, Optional, Union, overload
from typing_extensions import Self, override
from weakref import ref

import jieba
from cookit.loguru import warning_suppress
from cookit.pyd import model_validator, type_dump_python, type_validate_python
from nonebot import logger
from nonebot.plugin import Plugin, get_loaded_plugins
from pydantic import BaseModel, Field, PrivateAttr
from pypinyin import Style, pinyin

full_pkg_name_re = re.compile(r"^(nonebot[-_]plugin[-_])?(?P<name>.+)$")
pkg_name_re = re.compile(r"[A-Za-z0-9-_\.:]+")


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


class _NotCHNStr(str):
    __slots__ = ()


class TextChunk(NamedTuple):
    is_pinyin: bool
    text: str
    tone: int = 0

    @classmethod
    def from_pinyin_res(cls, text: str) -> Self:
        is_pinyin = not isinstance(text, _NotCHNStr)
        tone = 0
        if is_pinyin:
            text = text[:-1]
            tone = int(text[-1])
        return cls(is_pinyin=is_pinyin, text=text, tone=tone)

    @cached_property
    def casefold_str(self) -> str:
        return self.text.casefold()

    def __str__(self):
        return f"{self.text}{self.tone}" if self.is_pinyin else self.text


class TextChunkSequence(Sequence[TextChunk]):
    def __init__(self, iterable: Optional[Iterable[TextChunk]] = None):
        self.chunks = tuple(iterable) if iterable else ()

    @classmethod
    def from_raw(cls, text: str) -> Self:
        transformed = pinyin(
            jieba.lcut(text),
            style=Style.TONE3,
            errors=lambda x: _NotCHNStr(x),
            neutral_tone_with_five=True,
        )
        return cls(TextChunk.from_pinyin_res(x[0]) for x in transformed)

    @cached_property
    def casefold_str(self) -> str:
        return str(self).casefold()

    def __str__(self):
        return " ".join(str(x) for x in self)

    def __lt__(self, other: object):
        return self.chunks.__lt__(other)  # type: ignore

    def __gt__(self, other: object):
        return self.chunks.__gt__(other)  # type: ignore

    def __eq__(self, other: object):
        return self.chunks.__eq__(other)  # type: ignore

    @override
    def __iter__(self) -> Iterator[TextChunk]:
        return self.chunks.__iter__()

    @override
    def __len__(self) -> int:
        return self.chunks.__len__()

    @overload
    def __getitem__(self, index: int) -> TextChunk: ...
    @overload
    def __getitem__(self, index: slice) -> Self: ...
    @override
    def __getitem__(self, index: Union[int, slice]):
        if isinstance(index, slice):
            return type(self)(self.chunks[index])
        return self.chunks[index]


class PMDataItemRaw(BaseModel):
    func: str
    trigger_method: str
    trigger_condition: str
    brief_des: str
    detail_des: str

    # extension properties
    hidden: Union[bool, str] = Field(default=False, alias="pmn_hidden")
    template: Optional[str] = Field(default=None, alias="pmn_template")

    @cached_property
    def casefold_func(self) -> str:
        return self.func.casefold()

    @cached_property
    def func_pinyin(self) -> TextChunkSequence:
        return TextChunkSequence.from_raw(self.func)


class PMDataItem(PMDataItemRaw):
    pmn_hidden_v: bool = False

    @classmethod
    async def resolve(cls, plugin: Plugin, data: PMDataItemRaw) -> Self:
        data_dict: dict = type_dump_python(data, exclude_unset=True)
        if isinstance((hidden := data_dict.get("pmn_hidden")), str):
            data_dict["pmn_hidden_v"] = await resolve_func_hidden(plugin, hidden)
        ins = cls(**data_dict)
        ins.casefold_func = data.casefold_func
        ins.func_pinyin = data.func_pinyin
        return ins


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
    def normalize_input(cls, values: Any):  # noqa: N805
        if isinstance(values, PMNPluginExtra):
            values = type_dump_python(values, exclude_unset=True)
        if not isinstance(values, dict):
            raise TypeError(f"Expected dict, got {type(values)}")
        should_normalize_keys = {x for x in values if x.lower() in {"author"}}
        for key in should_normalize_keys:
            value = values[key]
            del values[key]
            values[key.lower()] = value
        return values


class PMNPluginInfoRaw(BaseModel):
    name: str
    author: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    usage: Optional[str] = None
    pm_data: Optional[list[PMDataItemRaw]] = None
    pmn: PMNDataRaw = PMNDataRaw()

    _resolved_pm_data: Optional[list[PMDataItem]] = PrivateAttr(None)

    @cached_property
    def casefold_name(self) -> str:
        return self.name.casefold()

    @cached_property
    def name_pinyin(self) -> TextChunkSequence:
        return TextChunkSequence.from_raw(self.name)

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
        ins.casefold_name = data.casefold_name
        ins.name_pinyin = data.name_pinyin
        return ins


def normalize_replace(name: str) -> str:
    return name.replace("-", " ").replace("_", " ").replace(".", " ").replace(":", " ")


def normalize_plugin_name(name: str) -> str:
    if m := full_pkg_name_re.match(name):
        name = m["name"]
    if pkg_name_re.match(name):
        name = normalize_replace(name)
    if name[0].isascii() and name.islower():
        name = name.title()
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

    name = normalize_plugin_name(meta.name if meta else plugin.id_)

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
    logger.success(f"Collected {len(infos)} plugin infos")
    infos.sort(key=lambda x: x.name_pinyin)
    return infos


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

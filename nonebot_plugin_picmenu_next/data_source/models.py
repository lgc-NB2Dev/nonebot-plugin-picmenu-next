import asyncio
from collections.abc import Awaitable
from functools import cached_property
from typing import Any, Optional, Union
from typing_extensions import Self
from weakref import ref

from cookit.loguru import warning_suppress
from cookit.pyd import model_validator, type_dump_python
from nonebot.plugin import Plugin
from pydantic import BaseModel, Field, PrivateAttr

from ..utils import call_entrypoint
from .pinyin import PinyinChunkSequence


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
    def func_pinyin(self) -> PinyinChunkSequence:
        return PinyinChunkSequence.from_raw(self.func)


class PMDataItem(PMDataItemRaw):
    hidden: bool = Field(default=False, alias="pmn_hidden")  # pyright: ignore[reportIncompatibleVariableOverride]

    @classmethod
    async def resolve(cls, plugin: Plugin, data: PMDataItemRaw) -> Self:
        data_dict: dict = type_dump_python(data, exclude_unset=True)
        if isinstance((hidden := data_dict.get("pmn_hidden")), str):
            data_dict["pmn_hidden"] = await resolve_func_hidden(plugin, hidden)
        ins = cls(**data_dict)
        ins.casefold_func = data.casefold_func
        ins.func_pinyin = data.func_pinyin
        return ins


class PMNDataRaw(BaseModel):
    hidden: Union[bool, str] = False
    markdown: bool = False
    template: Optional[str] = None


class PMNData(PMNDataRaw):
    hidden: bool = False  # pyright: ignore[reportIncompatibleVariableOverride]

    @classmethod
    async def resolve(cls, plugin: Plugin, data: PMNDataRaw) -> Self:
        data_dict: dict = type_dump_python(data, exclude_unset=True)
        if isinstance((hidden := data_dict.get("hidden")), str):
            data_dict["hidden"] = await resolve_func_hidden(plugin, hidden)
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

    _plugin_ref: Optional[ref[Plugin]] = PrivateAttr(None)
    _resolved_pm_data: Optional[list[PMDataItem]] = PrivateAttr(None)

    @cached_property
    def casefold_name(self) -> str:
        return self.name.casefold()

    @cached_property
    def name_pinyin(self) -> PinyinChunkSequence:
        return PinyinChunkSequence.from_raw(self.name)

    @property
    def plugin(self) -> Optional[Plugin]:
        if self._plugin_ref:
            return self._plugin_ref()
        return None

    @plugin.setter
    def plugin(self, plugin: Plugin):
        self._plugin_ref = ref(plugin)

    @cached_property
    def subtitle(self) -> str:
        return " | ".join(
            x
            for x in (
                f"By {self.author}" if self.author else None,
                f"v{self.version}" if self.version else None,
            )
            if x
        )

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
    pmn: PMNData = PMNData()  # pyright: ignore[reportIncompatibleVariableOverride]

    @classmethod
    async def resolve(
        cls,
        data: PMNPluginInfoRaw,
        plugin: Optional[Plugin] = None,
    ) -> Self:
        if (not plugin) and (not (plugin := data.plugin)):
            raise ValueError("Plugin ref is expired, please manually set")

        data_dict: dict = type_dump_python(data, exclude_unset=True)
        tasks: list[Awaitable] = []

        if pmn := data_dict.get("pmn"):

            async def _t():
                v = None
                with warning_suppress(
                    f"Failed to resolve PicMenu Next data of {plugin.id_}",
                ):
                    v = await PMNData.resolve(plugin, pmn)
                data_dict["pmn"] = v

            tasks.append(_t())

        await asyncio.gather(*tasks)

        ins = cls(**data_dict)
        ins.casefold_name = data.casefold_name
        ins.name_pinyin = data.name_pinyin
        ins.plugin = plugin
        return ins

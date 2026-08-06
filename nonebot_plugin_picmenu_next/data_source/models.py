from functools import cached_property
from typing import Any, TypeVar

from cookit.pyd import (
    PYDANTIC_V2,
    get_model_with_config,
    model_copy,
    model_fields_set,
    model_validator,
    model_with_model_config,
)
from nonebot import get_plugin
from nonebot.plugin import Plugin
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from ..utils import normalize_plugin_name
from .pinyin import PinyinChunkSequence

T = TypeVar("T")


if PYDANTIC_V2:
    compat_model_config: ConfigDict = {}
    CompatModel = BaseModel
else:
    compat_model_config: ConfigDict = {
        "arbitrary_types_allowed": True,
        "keep_untouched": (cached_property,),
    }
    CompatModel = get_model_with_config(compat_model_config)


class PMDataItem(CompatModel):
    _alc_cmd_id: str | None = PrivateAttr(default=None)

    func: str
    trigger_method: str
    trigger_condition: str
    brief_des: str
    detail_des: str

    # extension properties
    hidden: bool = Field(default=False, alias="pmn_hidden")
    template: str | None = Field(default=None, alias="pmn_template")

    @property
    def alc_cmd_id(self) -> str | None:
        return self._alc_cmd_id

    @cached_property
    def casefold_func(self) -> str:
        return self.func.casefold()

    @cached_property
    def func_pinyin(self) -> PinyinChunkSequence:
        return PinyinChunkSequence.from_raw(self.func)


class OptionalPMDataItem(CompatModel):
    func: str | None = None
    trigger_method: str | None = None
    trigger_condition: str | None = None
    brief_des: str | None = None
    detail_des: str | None = None

    # extension properties
    hidden: bool | None = Field(default=None, alias="pmn_hidden")
    template: str | None = Field(default=None, alias="pmn_template")


class PMNData(CompatModel):
    hidden: bool = False
    markdown: bool = False
    template: str | None = None
    inherit_func_template: bool = True
    alc_force_enable_detect: bool = False


@model_with_model_config({**compat_model_config, "extra": "forbid"})
class ExternalPMNData(CompatModel):
    hidden: bool = False
    markdown: bool = False
    template: str | None = None
    inherit_func_template: bool = True

    def to_pmn_data(self) -> PMNData:
        return PMNData(
            **{k: getattr(self, k) for k in model_fields_set(self)},
        )


class PMNPluginExtra(CompatModel):
    author: str | list[str] | None = None
    version: str | None = None
    menu_data: list[PMDataItem] | None = None
    pmn: PMNData | None = None


class OptionalPMNPluginInfo(CompatModel):
    name: str | None = None
    plugin_id: str | None = None
    author: str | None = None
    version: str | None = None
    description: str | None = None
    usage: str | None = None
    pm_data: list[PMDataItem] | None = None
    pmn: PMNData = PMNData()
    supported_adapters: set[str] | None = None

    def to_required(self, name: str | None = None):
        if name is None and self.name is None:
            raise ValueError("`name` is required for PMNPluginInfo")
        data = {k: getattr(self, k) for k in model_fields_set(self)}
        if name:
            data["name"] = name
        return PMNPluginInfo(**data)


class PMNPluginInfo(CompatModel):
    name: str
    plugin_id: str | None = None
    author: str | None = None
    version: str | None = None
    description: str | None = None
    usage: str | None = None
    pm_data: list[PMDataItem] | None = None
    pmn: PMNData = PMNData()
    supported_adapters: set[str] | None = None

    @cached_property
    def casefold_name(self) -> str:
        return self.name.casefold()

    @cached_property
    def name_pinyin(self) -> PinyinChunkSequence:
        return PinyinChunkSequence.from_raw(self.name)

    @property
    def subtitle(self) -> str:
        return " | ".join(
            x
            for x in (
                f"By {self.author}" if self.author else None,
                f"v{self.version}" if self.version else None,
            )
            if x
        )

    @property
    def plugin(self) -> Plugin | None:
        return get_plugin(self.plugin_id) if self.plugin_id else None


class ExternalPluginInfo(CompatModel):
    name: str | None = None
    author: str | None = None
    version: str | None = None
    description: str | None = None
    usage: str | None = None
    funcs: list[PMDataItem] | None = None
    pmn: ExternalPMNData = ExternalPMNData()
    supported_adapters: set[str] | None = None

    @model_validator(mode="before")
    def normalize_input(cls, values: Any):  # noqa: N805
        # these params cannot be explicitly none
        if not isinstance(values, dict):
            return values
        for key in ("name", "funcs"):
            if key in values and values[key] is None:
                raise ValueError(f"`{key}` cannot be null")
        return values

    def has_func_override(self) -> bool:
        return "funcs" in model_fields_set(self)

    def to_optional_plugin_info(self, plugin_id: str | None = None):
        key_name_map = {"funcs": "pm_data"}
        data: dict[str, Any] = {}
        for k in model_fields_set(self):
            if k == "pmn" and not model_fields_set(self.pmn):
                continue
            data[key_name_map.get(k, k)] = (
                self.pmn.to_pmn_data() if k == "pmn" else getattr(self, k)
            )
        if plugin_id:
            data["plugin_id"] = plugin_id
        return OptionalPMNPluginInfo(**data)

    def to_plugin_info(self, plugin_id: str | None = None, name: str | None = None):
        if name is None:
            if self.name is not None:
                name = self.name
            elif plugin_id:
                name = normalize_plugin_name(plugin_id)
        if name is None:
            raise ValueError(
                "`name` is required for PMNPluginInfo"
                ", please set `name` to this model instance or pass it in"
                ", or pass `plugin_id` to generate one",
            )
        info = self.to_optional_plugin_info(plugin_id)
        return info.to_required(name=name)

    def merge_to(
        self,
        other: PMNPluginInfo,
        plugin_id: str | None = None,
        copy: bool = True,
    ):
        if copy:
            other = model_copy(other, deep=True)

        if plugin_id:
            other.plugin_id = plugin_id

        for k in model_fields_set(self):
            if k == "funcs":
                other.pm_data = self.funcs
            elif k == "pmn":  # shallow copy pmn
                for k in model_fields_set(self.pmn):
                    setattr(other.pmn, k, getattr(self.pmn, k))
            else:
                setattr(other, k, getattr(self, k))
        return other

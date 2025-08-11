from functools import cached_property
from typing import Any, TypeVar

from cookit.pyd import (
    PYDANTIC_V2,
    get_model_with_config,
    model_copy,
    model_fields_set,
    model_validator,
    type_dump_python,
)
from nonebot import get_plugin
from nonebot.plugin import Plugin
from pydantic import BaseModel, Field

from .pinyin import PinyinChunkSequence

T = TypeVar("T")


if PYDANTIC_V2:
    CompatModel = BaseModel
else:
    CompatModel = get_model_with_config(
        {
            "arbitrary_types_allowed": True,
            "keep_untouched": (cached_property,),
        },
    )


class PMDataItem(CompatModel):
    func: str
    trigger_method: str
    trigger_condition: str
    brief_des: str
    detail_des: str

    # extension properties
    hidden: bool = Field(default=False, alias="pmn_hidden")
    template: str | None = Field(default=None, alias="pmn_template")

    @cached_property
    def casefold_func(self) -> str:
        return self.func.casefold()

    @cached_property
    def func_pinyin(self) -> PinyinChunkSequence:
        return PinyinChunkSequence.from_raw(self.func)


class PMNData(CompatModel):
    hidden: bool = False
    hidden_mixin: str | None = None
    func_hidden_mixin: str | None = None
    markdown: bool = False
    template: str | None = None


class PMNPluginExtra(CompatModel):
    author: str | list[str] | None = None
    version: str | None = None
    menu_data: list[PMDataItem] | None = None
    pmn: PMNData | None = None

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


class PMNPluginInfo(CompatModel):
    name: str
    plugin_id: str | None = None
    author: str | None = None
    version: str | None = None
    description: str | None = None
    usage: str | None = None
    pm_data: list[PMDataItem] | None = None
    pmn: PMNData = PMNData()

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
    name: str
    author: str | None = None
    version: str | None = None
    description: str | None = None
    usage: str | None = None
    funcs: list[PMDataItem] | None = None
    pmn: PMNData = PMNData()

    def to_plugin_info(self, plugin_id: str | None = None):
        key_name_map = {"funcs": "pm_data"}
        data = {
            key_name_map.get(k, k): getattr(self, k) for k in model_fields_set(self)
        }
        if plugin_id:
            data["plugin_id"] = plugin_id
        return PMNPluginInfo(**data)

    def merge_to(
        self,
        other: PMNPluginInfo,
        plugin_id: str | None = None,
        copy: bool = True,
    ):
        if copy:
            other = model_copy(other)
        this = self.to_plugin_info(plugin_id)
        for k in model_fields_set(this):
            setattr(other, k, getattr(this, k))
        return other

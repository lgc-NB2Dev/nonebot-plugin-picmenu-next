from functools import cached_property
from typing import Any, Optional, TypeVar, Union

from cookit.pyd import (
    PYDANTIC_V2,
    get_model_with_config,
    model_validator,
    type_dump_python,
)
from nonebot import get_plugin
from nonebot.plugin import Plugin
from pydantic import BaseModel, ConfigDict, Field

from .pinyin import PinyinChunkSequence

T = TypeVar("T")


if PYDANTIC_V2:
    CompatModel = BaseModel
else:
    CompatModel = get_model_with_config(
        {
            "arbitrary_types_allowed": True,
            "keep_untouched": (cached_property,),
        }
    )


class PMDataItem(CompatModel):
    func: str
    trigger_method: str
    trigger_condition: str
    brief_des: str
    detail_des: str

    # extension properties
    hidden: bool = Field(default=False, alias="pmn_hidden")
    template: Optional[str] = Field(default=None, alias="pmn_template")

    @cached_property
    def casefold_func(self) -> str:
        return self.func.casefold()

    @cached_property
    def func_pinyin(self) -> PinyinChunkSequence:
        return PinyinChunkSequence.from_raw(self.func)


class PMNData(BaseModel):
    hidden: bool = False
    hidden_mixin: Optional[str] = None
    func_hidden_mixin: Optional[str] = None
    markdown: bool = False
    template: Optional[str] = None


class PMNPluginExtra(BaseModel):
    author: Union[str, list[str], None] = None
    version: Optional[str] = None
    menu_data: Optional[list[PMDataItem]] = None
    pmn: Optional[PMNData] = None

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
    plugin_id: Optional[str] = None
    author: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    usage: Optional[str] = None
    pm_data: Optional[list[PMDataItem]] = None
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
    def plugin(self) -> Optional[Plugin]:
        return get_plugin(self.plugin_id) if self.plugin_id else None

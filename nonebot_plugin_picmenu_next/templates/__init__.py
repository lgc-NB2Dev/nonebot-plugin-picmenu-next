from pathlib import Path
from typing import Callable, Optional, Protocol, TypeVar

from cookit import HasNameProtocol, NameDecoCollector, auto_import
from nonebot import logger
from nonebot_plugin_alconna.uniseg import UniMessage

from ..config import config
from ..data_source import PMDataItem, PMNPluginInfo

TN = TypeVar("TN", bound=HasNameProtocol)


class IndexTemplateHandler(HasNameProtocol, Protocol):
    async def __call__(self, infos: list[PMNPluginInfo]) -> UniMessage: ...


class DetailTemplateHandler(HasNameProtocol, Protocol):
    async def __call__(self, info: PMNPluginInfo, info_index: int) -> UniMessage: ...


class FuncDetailTemplateHandler(HasNameProtocol, Protocol):
    async def __call__(
        self,
        info: PMNPluginInfo,
        info_index: int,
        func: PMDataItem,
        func_index: int,
    ) -> UniMessage: ...


class TemplateDecoCollector(NameDecoCollector[TN]):
    def __init__(
        self,
        template_type: str,
        template_name_getter: Callable[[], str],
        data: Optional[dict[str, TN]] = None,
        allow_overwrite: bool = False,
    ) -> None:
        super().__init__(data, allow_overwrite)
        self.template_type = template_type
        self.name_getter = template_name_getter

    def get(self, name: Optional[str] = None) -> TN:
        if name and name not in self.data:
            logger.warning(
                f"Plugin configured {self.template_type} template '{name}' not found"
                ", falling back to user configured default",
            )
            name = None
        if not name:
            name = self.name_getter()
        if name not in self.data:
            logger.warning(
                f"User configured {self.template_type} template '{name}' not found"
                ", falling back to plugin default",
            )
            name = "default"
        return self.data[name]


index_templates = TemplateDecoCollector[IndexTemplateHandler](
    "index",
    lambda: config.index_template,
)
detail_templates = TemplateDecoCollector[DetailTemplateHandler](
    "detail",
    lambda: config.detail_template,
)
func_detail_templates = TemplateDecoCollector[FuncDetailTemplateHandler](
    "func detail",
    lambda: config.func_detail_template,
)


def load_builtin_templates():
    auto_import(Path(__file__).parent, __package__)

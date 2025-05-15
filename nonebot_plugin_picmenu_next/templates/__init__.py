from pathlib import Path
from typing import Optional, Protocol, TypeVar

from cookit import HasNameProtocol, NameDecoCollector, auto_import
from nonebot import logger
from nonebot_plugin_alconna.uniseg import UniMessage

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
        data: Optional[dict[str, TN]] = None,
        allow_overwrite: bool = False,
    ) -> None:
        super().__init__(data, allow_overwrite)
        self.template_type = template_type

    def get(self, name: str) -> TN:
        if name not in self.data:
            logger.warning(
                f"{self.template_type} template '{name}' not found"
                ", falling back to default",
            )
            name = "default"
        return self.data[name]


index_templates = TemplateDecoCollector[IndexTemplateHandler]("index")
detail_templates = TemplateDecoCollector[DetailTemplateHandler]("detail")
func_detail_templates = TemplateDecoCollector[FuncDetailTemplateHandler]("func detail")


def load_builtin_templates():
    auto_import(Path(__file__).parent, __package__)

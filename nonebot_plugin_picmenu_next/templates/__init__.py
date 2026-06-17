from collections.abc import Callable, Iterable
from importlib import import_module
from pathlib import Path
from typing import Protocol, TypeVar

from cookit import HasNameProtocol, NameDecoCollector
from nonebot import logger
from nonebot_plugin_alconna.uniseg import UniMessage

from ..config import config
from ..data_source.models import PMDataItem, PMNPluginInfo

TN = TypeVar("TN", bound=HasNameProtocol)

BUILTIN_TEMPLATE_DIR = Path(__file__).parent
loaded_builtin_templates: set[str] = set()


def is_builtin_template(name: str) -> bool:
    if not name or name.startswith("_"):
        return False
    path = BUILTIN_TEMPLATE_DIR / name
    return path.is_dir() and (path / "__init__.py").exists()


def load_builtin_template(name: str) -> bool:
    if not is_builtin_template(name):
        return False
    if name not in loaded_builtin_templates:
        import_module(f".{name}", __package__)
        loaded_builtin_templates.add(name)
    return True


class IndexTemplateHandler(HasNameProtocol, Protocol):
    async def __call__(
        self,
        infos: list[PMNPluginInfo],
        showing_hidden: bool,
        user_can_see_hidden: bool | None,
    ) -> UniMessage: ...


class DetailTemplateHandler(HasNameProtocol, Protocol):
    async def __call__(
        self,
        info: PMNPluginInfo,
        info_index: int,
        showing_hidden: bool,
        user_can_see_hidden: bool | None,
    ) -> UniMessage: ...


class FuncDetailTemplateHandler(HasNameProtocol, Protocol):
    async def __call__(
        self,
        info: PMNPluginInfo,
        info_index: int,
        func: PMDataItem,
        func_index: int | None,
        showing_hidden: bool,
        user_can_see_hidden: bool | None,
    ) -> UniMessage: ...


class TemplateDecoCollector(NameDecoCollector[TN]):
    def __init__(
        self,
        template_type: str,
        template_name_getter: Callable[[], str],
        data: dict[str, TN] | None = None,
        allow_overwrite: bool = False,
    ) -> None:
        super().__init__(data, allow_overwrite)
        self.template_type = template_type
        self.name_getter = template_name_getter

    def get(self, name: str | None = None) -> TN:
        if name:
            load_builtin_template(name)
        if name and name not in self.data:
            logger.warning(
                f"Plugin configured {self.template_type} template '{name}' not found"
                ", falling back to user configured default",
            )
            name = None
        if not name:
            name = self.name_getter()
            load_builtin_template(name)
        if name not in self.data:
            logger.warning(
                f"User configured {self.template_type} template '{name}' not found"
                ", falling back to plugin default",
            )
            name = "default"
            load_builtin_template(name)
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


def preload_builtin_templates():
    for name in {
        config.index_template,
        config.detail_template,
        config.func_detail_template,
    }:
        load_builtin_template(name)


def preload_builtin_templates_from_infos(infos: Iterable[PMNPluginInfo]) -> None:
    names: set[str] = set()
    for info in infos:
        if info.pmn.template:
            names.add(info.pmn.template)
        for item in info.pm_data or ():
            if item.template:
                names.add(item.template)

    for name in names:
        load_builtin_template(name)

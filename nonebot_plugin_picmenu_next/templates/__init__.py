from collections.abc import Awaitable
from pathlib import Path
from typing import Callable
from typing_extensions import TypeAlias

from cookit import NameDecoCollector, auto_import
from nonebot_plugin_alconna.uniseg import UniMessage

from ..data_source import PMDataItem, PMNPluginInfo

IndexTemplateHandler: TypeAlias = Callable[[list[PMNPluginInfo]], Awaitable[UniMessage]]
DetailTemplateHandler: TypeAlias = Callable[[PMNPluginInfo], Awaitable[UniMessage]]
FuncDetailTemplateHandler: TypeAlias = Callable[
    [PMNPluginInfo, PMDataItem],
    Awaitable[UniMessage],
]

index_template = NameDecoCollector[IndexTemplateHandler]()
detail_template = NameDecoCollector[DetailTemplateHandler]()
func_detail_template = NameDecoCollector[FuncDetailTemplateHandler]()


def load_builtin_templates():
    auto_import(Path(__file__).parent, __package__)

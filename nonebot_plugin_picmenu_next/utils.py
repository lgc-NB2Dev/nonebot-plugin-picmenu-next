import importlib
import re
from asyncio import iscoroutinefunction
from typing import Any

from nonebot.plugin import Plugin

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

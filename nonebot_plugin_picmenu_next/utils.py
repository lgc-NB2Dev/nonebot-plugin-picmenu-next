import re

full_pkg_name_re = re.compile(r"^(nonebot[-_]plugin[-_])?(?P<name>.+)$")
pkg_name_re = re.compile(r"[A-Za-z0-9-_\.:]+")


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

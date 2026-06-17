import re
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote

from cookit.pw import RouterGroup, make_real_path_router
from cookit.pw.loguru import log_router_err
from nonebot.plugin import Plugin

from ..data_source.models import PMNPluginInfo

if TYPE_CHECKING:
    from playwright.async_api import Route
    from yarl import URL

ROUTE_BASE_URL = "https://picmenu-next.nonebot"


def local_file_route_prp_transformer(
    path: str, module_path: Path, _info: PMNPluginInfo, _plugin: Plugin
) -> str:
    return f"/local-file?path={quote(str(module_path.joinpath(path)))}"


base_routers = RouterGroup()


@base_routers.router(f"{ROUTE_BASE_URL}/")
@log_router_err()
async def _(route: "Route", **_):
    await route.fulfill(content_type="text/html", body="<html></html>")


@base_routers.router(re.compile(rf"^{ROUTE_BASE_URL}/local-file\?path=[^/]+"))
@make_real_path_router
@log_router_err()
async def _(url: "URL", **_):
    return Path(url.query["path"]).resolve()  # noqa: ASYNC240

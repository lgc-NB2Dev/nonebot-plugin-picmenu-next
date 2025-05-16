import re
from pathlib import Path
from typing import TYPE_CHECKING

from cookit.pw import RouterGroup, make_real_path_router
from cookit.pw.loguru import log_router_err

if TYPE_CHECKING:
    from playwright.async_api import Route
    from yarl import URL


ROUTE_BASE_URL = "https://picmenu-next.nonebot"

base_routers = RouterGroup()


@base_routers.router(f"{ROUTE_BASE_URL}/")
@log_router_err()
async def _(route: "Route", **_):
    await route.fulfill(content_type="text/html", body="<h1>Hello World!</h1>")


@base_routers.router(re.compile(rf"^{ROUTE_BASE_URL}/local-file\?path=[^/]+"))
@make_real_path_router
@log_router_err()
async def _(url: "URL", **_):
    return Path(url.query["path"]).resolve()

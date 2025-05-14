import re
from pathlib import Path
from typing import TYPE_CHECKING

import jinja2 as jj
from cookit import DebugFileWriter
from cookit.jinja import register_all_filters
from cookit.pw import RouterGroup, make_real_path_router, screenshot_html
from cookit.pw.loguru import log_router_err
from cookit.pyd import model_with_alias_generator
from nonebot import get_plugin_config
from nonebot_plugin_akinator.render import router_group
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_htmlrender import get_new_page
from pydantic import BaseModel, Field

from ...data_source import PMNPluginInfo
from .. import index_template

if TYPE_CHECKING:
    from playwright.async_api import Route
    from yarl import URL


@model_with_alias_generator(lambda x: f"pmn_default_{x}")
class TemplateConfigModel(BaseModel):
    command_start: set[str] = Field(alias="command_start")

    dark: bool = False
    additional_css: list[str]
    additional_js: list[str]

    @property
    def pfx(self) -> str:
        return next(iter(self.command_start), "")


template_config = get_plugin_config(TemplateConfigModel)


RES_DIR = Path(__file__).parent / "res"
ROUTE_BASE_URL = "https://picmenu-next.nonebot"
debug = DebugFileWriter(Path.cwd() / "debug", "picmenu-next", "default")

jj_env = jj.Environment(
    loader=jj.FileSystemLoader(Path(__file__).parent / "res" / "templates"),
    autoescape=True,
    enable_async=True,
)
register_all_filters(jj_env)

base_routers = RouterGroup()


@router_group.router(f"{ROUTE_BASE_URL}/")
@log_router_err()
async def _(route: "Route", **_):
    await route.fulfill(content_type="text/html", body="<h1>Hello World!</h1>")


@router_group.router(re.compile(rf"^{ROUTE_BASE_URL}/local-file\?path=[^/]+"))
@make_real_path_router
@log_router_err()
async def _(url: "URL", **_):
    return Path(url.query["path"]).resolve()


@router_group.router(f"{ROUTE_BASE_URL}/**/*", 99)
@make_real_path_router
@log_router_err()
async def _(url: "URL", **_):
    return RES_DIR.joinpath(*url.parts[1:])


@index_template("default")
async def render_index(infos: list[PMNPluginInfo]) -> UniMessage:
    template = jj_env.get_template("index.html.jinja")
    html = await template.render_async(infos=infos, cfg=template_config)
    if debug.enabled:
        debug.write("index_{time}.html", html)
    async with get_new_page() as page:
        await page.goto(f"{ROUTE_BASE_URL}/")
        pic = await screenshot_html(page, html)
    return UniMessage.image(raw=pic)

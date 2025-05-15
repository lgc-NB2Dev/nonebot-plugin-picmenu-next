import re
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

import jinja2 as jj
from cookit import DebugFileWriter
from cookit.jinja import register_all_filters
from cookit.pw import RouterGroup, make_real_path_router, screenshot_html
from cookit.pw.loguru import log_router_err
from cookit.pyd import model_with_alias_generator
from nonebot import get_plugin_config
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_htmlrender import get_new_page
from pydantic import BaseModel, Field

from ...data_source import PMDataItem, PMNPluginInfo
from .. import detail_templates, func_detail_templates, index_templates

if TYPE_CHECKING:
    from playwright.async_api import Route
    from yarl import URL


@model_with_alias_generator(lambda x: f"pmn_default_{x}")
class TemplateConfigModel(BaseModel):
    command_start: set[str] = Field(alias="command_start")

    dark: bool = False
    additional_css: list[str] = []
    additional_js: list[str] = []

    @cached_property
    def pfx(self) -> str:
        return next(iter(self.command_start), "")


template_config = get_plugin_config(TemplateConfigModel)


RES_DIR = Path(__file__).parent / "res"
ROUTE_BASE_URL = "https://picmenu-next.nonebot"
debug = DebugFileWriter(Path.cwd() / "debug", "picmenu-next", "default")

jj_env = jj.Environment(
    loader=jj.FileSystemLoader(Path(__file__).parent / "res"),
    autoescape=True,
    enable_async=True,
)
register_all_filters(jj_env)

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


@base_routers.router(f"{ROUTE_BASE_URL}/**/*", 99)
@make_real_path_router
@log_router_err()
async def _(url: "URL", **_):
    return RES_DIR.joinpath(*url.parts[1:])


def version():
    from ... import __version__

    return __version__


async def render(template: str, routers: RouterGroup, **kwargs):
    template_obj = jj_env.get_template(template)
    html = await template_obj.render_async(
        **kwargs,
        cfg=template_config,
        version=version(),
    )
    if debug.enabled:
        debug.write(html, f"{template.replace('.html.jinja', '')}_{{time}}.html")

    async with get_new_page() as page:
        await routers.apply(page)
        await page.goto(f"{ROUTE_BASE_URL}/")
        pic = await screenshot_html(page, html, selector="main")
    return UniMessage.image(raw=pic)


@index_templates("default")
async def render_index(infos: list[PMNPluginInfo]) -> UniMessage:
    routers = base_routers.copy()
    return await render(
        "index.html.jinja",
        routers,
        infos=infos,
    )


def get_plugin_desc(info: PMNPluginInfo):
    return " | ".join(
        x
        for x in (
            f"By {info.author}" if info.author else None,
            f"v{info.version}" if info.version else None,
        )
        if x
    )


@detail_templates("default")
async def render_detail(info: PMNPluginInfo, info_index: int) -> UniMessage:
    routers = base_routers.copy()
    return await render(
        "detail.html.jinja",
        routers,
        info=info,
        info_index=info_index,
        desc=get_plugin_desc(info),
    )


@func_detail_templates("default")
async def render_func_detail(
    info: PMNPluginInfo,
    info_index: int,
    func: PMDataItem,
    func_index: int,
) -> UniMessage:
    routers = base_routers.copy()
    return await render(
        "detail.html.jinja",
        routers,
        info=info,
        info_index=info_index,
        desc=get_plugin_desc(info),
        func=func,
        func_index=func_index,
    )

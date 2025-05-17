from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

import jinja2 as jj
from cookit import DebugFileWriter
from cookit.pw import RouterGroup, make_real_path_router, screenshot_html
from cookit.pw.loguru import log_router_err
from cookit.pyd import model_with_alias_generator
from nonebot import get_plugin_config
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_htmlrender import get_new_page
from pydantic import BaseModel, Field

from ...config import version
from ...data_source.models import PMDataItem, PMNPluginInfo
from .. import detail_templates, func_detail_templates, index_templates
from ..pw_utils import ROUTE_BASE_URL, base_routers, register_filters

if TYPE_CHECKING:
    from yarl import URL


@model_with_alias_generator(lambda x: f"pmn_default_{x}")
class TemplateConfigModel(BaseModel):
    command_start: set[str] = Field(alias="command_start")

    dark: bool = False
    enable_builtin_code_css: bool = True
    additional_css: list[str] = []
    additional_js: list[str] = []

    @cached_property
    def pfx(self) -> str:
        return next(iter(self.command_start), "")


template_config = get_plugin_config(TemplateConfigModel)


RES_DIR = Path(__file__).parent / "res"
jj_env = jj.Environment(
    loader=jj.FileSystemLoader(RES_DIR),
    autoescape=True,
    enable_async=True,
)
register_filters(jj_env)

debug = DebugFileWriter(Path.cwd() / "debug", "picmenu-next", "default")


base_routers = base_routers.copy()


@base_routers.router(f"{ROUTE_BASE_URL}/**/*", 99)
@make_real_path_router
@log_router_err()
async def _(url: "URL", **_):
    return RES_DIR.joinpath(*url.parts[1:])


async def render(template: str, routers: RouterGroup, **kwargs):
    template_obj = jj_env.get_template(template)
    html = await template_obj.render_async(
        **kwargs,
        cfg=template_config,
        version=version(),
    )
    if debug.enabled:
        debug.write(html, f"{template.replace('.html.jinja', '')}_{{time}}.html")

    async with get_new_page(viewport={"width": 1920, "height": 5400}) as page:
        await routers.apply(page)
        await page.goto(f"{ROUTE_BASE_URL}/")
        pic = await screenshot_html(page, html, selector="main", type="jpeg")
    return UniMessage.image(raw=pic)


@index_templates("default")
async def render_index(
    infos: list[PMNPluginInfo],
    showing_hidden: bool,
) -> UniMessage:
    routers = base_routers.copy()
    return await render(
        "index.html.jinja",
        routers,
        infos=infos,
        showing_hidden=showing_hidden,
    )


@detail_templates("default")
async def render_detail(
    info: PMNPluginInfo,
    info_index: int,
    showing_hidden: bool,
) -> UniMessage:
    routers = base_routers.copy()
    return await render(
        "detail.html.jinja",
        routers,
        info=info,
        info_index=info_index,
        showing_hidden=showing_hidden,
    )


@func_detail_templates("default")
async def render_func_detail(
    info: PMNPluginInfo,
    info_index: int,
    func: PMDataItem,
    func_index: int,
    showing_hidden: bool,
) -> UniMessage:
    routers = base_routers.copy()
    return await render(
        "detail.html.jinja",
        routers,
        info=info,
        info_index=info_index,
        func=func,
        func_index=func_index,
        showing_hidden=showing_hidden,
    )

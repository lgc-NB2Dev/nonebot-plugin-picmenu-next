# ruff: noqa: E402

from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

import jinja2 as jj
from cookit import DebugFileWriter
from cookit.pw import RouterGroup, make_real_path_router, screenshot_html
from cookit.pw.loguru import log_router_err
from cookit.pyd.compat import get_model_with_config
from nonebot import get_plugin_config
from nonebot.plugin import require
from nonebot_plugin_alconna.uniseg import UniMessage
from pydantic import Field

from ...config import version
from ...data_source.models import PMDataItem, PMNPluginInfo, compat_model_config
from .. import detail_templates, func_detail_templates, index_templates
from ..jj_utils import setup_base_filters
from ..pw_utils import ROUTE_BASE_URL, base_routers

if TYPE_CHECKING:
    from playwright.async_api import Page
    from yarl import URL

require("nonebot_plugin_htmlrender")

from nonebot_plugin_htmlrender.consts import RenderBackend

from ..hr_utils import HTMLRENDER_MD_TEMPLATE_DIR, get_template_render

## Config

AliasCompatModel = get_model_with_config(
    {
        "alias_generator": lambda x: f"pmn_default_{x}",
        **compat_model_config,
    },
)


class TemplateConfigModel(AliasCompatModel):
    command_start: set[str] = Field(alias="command_start")

    dark: bool = False
    enable_builtin_code_css: bool = True
    additional_css: list[str] = Field(default_factory=list)
    additional_js: list[str] = Field(default_factory=list)

    @cached_property
    def pfx(self) -> str:
        return next(iter(self.command_start), "")


template_config = get_plugin_config(TemplateConfigModel)


## Consts / Vars

RES_DIR = Path(__file__).parent / "res"
debug = DebugFileWriter(Path.cwd() / "debug", "picmenu-next", "default")
template_render = get_template_render(
    None,
    frozenset({RenderBackend.PLAYWRIGHT}),
    "PicMenu default template",
    fallback_backend=RenderBackend.PLAYWRIGHT,
)[0]


## Filters / Jinja

filters = setup_base_filters()

jj_env = jj.Environment(
    loader=jj.FileSystemLoader(RES_DIR),
    autoescape=True,
    enable_async=True,
)
jj_env.filters.update(filters.data)


## Routers

base_routers = base_routers.copy()


@base_routers.router(f"{ROUTE_BASE_URL}/markdown/**/*")
@make_real_path_router
@log_router_err()
async def _(url: "URL", **_):
    return HTMLRENDER_MD_TEMPLATE_DIR.joinpath(*url.parts[2:])


@base_routers.router(f"{ROUTE_BASE_URL}/**/*", 99)
@make_real_path_router
@log_router_err()
async def _(url: "URL", **_):
    return RES_DIR.joinpath(*url.parts[1:])


## Render


async def render(template: str, routers: RouterGroup, **kwargs):
    template_obj = jj_env.get_template(template)
    html = await template_obj.render_async(
        **kwargs,
        cfg=template_config,
        version=version(),
    )
    if debug.enabled:
        debug.write(html, f"{template.replace('.html.jinja', '')}_{{time}}.html")

    async with template_render.get_render_context(
        viewport={"width": 810, "height": 2430}
    ) as page:
        if TYPE_CHECKING:
            assert isinstance(page, Page)
        await routers.apply(page)
        await page.goto(f"{ROUTE_BASE_URL}/")
        pic = await screenshot_html(page, html, selector="main", type="jpeg")
    return UniMessage.image(raw=pic)


@index_templates("default")
async def render_index(
    infos: list[PMNPluginInfo],
    showing_hidden: bool,
    user_can_see_hidden: bool | None,
) -> UniMessage:
    routers = base_routers.copy()
    return await render(
        "index.html.jinja",
        routers,
        infos=infos,
        showing_hidden=showing_hidden,
        user_can_see_hidden=user_can_see_hidden,
    )


@detail_templates("default")
async def render_detail(
    info: PMNPluginInfo,
    info_index: int,
    showing_hidden: bool,
    user_can_see_hidden: bool | None,
) -> UniMessage:
    routers = base_routers.copy()
    return await render(
        "detail.html.jinja",
        routers,
        info=info,
        info_index=info_index,
        showing_hidden=showing_hidden,
        user_can_see_hidden=user_can_see_hidden,
    )


@func_detail_templates("default")
async def render_func_detail(
    info: PMNPluginInfo,
    info_index: int,
    func: PMDataItem,
    func_index: int | None,
    showing_hidden: bool,
    user_can_see_hidden: bool | None,
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
        user_can_see_hidden=user_can_see_hidden,
    )

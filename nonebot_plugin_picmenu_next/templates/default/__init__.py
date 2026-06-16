from functools import cached_property
from pathlib import Path

import jinja2 as jj
from cookit import DebugFileWriter
from cookit.pyd.compat import get_model_with_config
from nonebot import get_plugin_config
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_htmlrender.backend.playwright.models import (
    ContentConfig,
    HtmlRenderRequest,
    JpegScreenshotOptions,
    PageConfig,
    RenderConfig,
    ViewportConfig,
)
from nonebot_plugin_htmlrender.consts import RenderBackend
from pydantic import Field

from ...config import version
from ...data_source.models import PMDataItem, PMNPluginInfo, compat_model_config
from .. import detail_templates, func_detail_templates, index_templates
from ..t_utils import get_template_render, read_local_file, register_filters

AliasCompatModel = get_model_with_config(
    {
        "alias_generator": lambda x: f"pmn_default_{x}",
        **compat_model_config,
    },
)


class TemplateConfigModel(AliasCompatModel):
    command_start: set[str] = Field(alias="command_start")

    render_backend: RenderBackend | None = None
    dark: bool = False
    enable_builtin_code_css: bool = True
    additional_css: list[str] = Field(default_factory=list)

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

SUPPORTED_RENDER_BACKENDS = frozenset({RenderBackend.PLAYWRIGHT})
template_render = get_template_render(
    template_config.render_backend,
    SUPPORTED_RENDER_BACKENDS,
    "PicMenu default template",
)


def read_res(path: str) -> str:
    return read_local_file(RES_DIR / path)


async def render(template: str, **kwargs):
    template_obj = jj_env.get_template(template)
    html = await template_obj.render_async(
        **kwargs,
        cfg=template_config,
        read_local_file=read_local_file,
        read_res=read_res,
        version=version(),
    )
    if debug.enabled:
        debug.write(html, f"{template.replace('.html.jinja', '')}_{{time}}.html")

    request = HtmlRenderRequest(
        content=ContentConfig(html=html),
        render=RenderConfig(
            page=PageConfig(
                viewport=ViewportConfig(width=810, height=10),
            ),
            screenshot=JpegScreenshotOptions(full_page=True),
        ),
    )
    pic = await template_render.render_html(request)
    return UniMessage.image(raw=pic)


@index_templates("default")
async def render_index(
    infos: list[PMNPluginInfo],
    showing_hidden: bool,
    user_can_see_hidden: bool | None,
) -> UniMessage:
    return await render(
        "index.html.jinja",
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
    return await render(
        "detail.html.jinja",
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
    return await render(
        "detail.html.jinja",
        info=info,
        info_index=info_index,
        func=func,
        func_index=func_index,
        showing_hidden=showing_hidden,
        user_can_see_hidden=user_can_see_hidden,
    )

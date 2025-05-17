import re
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cookit.jinja import cookit_global_filter
from cookit.jinja.filters import br, safe_layout, space
from cookit.loguru import warning_suppress
from cookit.pw import RouterGroup, make_real_path_router
from cookit.pw.loguru import log_router_err
from markdown_it import MarkdownIt
from markupsafe import Markup
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.tasklists import tasklists_plugin
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from ..ft_parser import transform_ft

if TYPE_CHECKING:
    import jinja2 as jj
    from playwright.async_api import Route
    from yarl import URL


ROUTE_BASE_URL = "https://picmenu-next.nonebot"

base_routers = RouterGroup()
filters = type(cookit_global_filter)(cookit_global_filter.data.copy())


def highlight_code(code: str, name: str, _attrs: Any):
    if name:
        with warning_suppress(f"Failed to highlight code, lang: {name}"):
            lexer = get_lexer_by_name(name)
            formatter = HtmlFormatter(nowrap=True)
            return highlight(code, lexer, formatter)
    return escape(code)


md = (
    MarkdownIt("commonmark", {"highlight": highlight_code})
    .enable(["strikethrough", "linkify", "table"])
    .use(tasklists_plugin, enabled=True)
    .use(dollarmath_plugin)
)


@base_routers.router(f"{ROUTE_BASE_URL}/")
@log_router_err()
async def _(route: "Route", **_):
    await route.fulfill(content_type="text/html", body="<h1>Hello World!</h1>")


@base_routers.router(re.compile(rf"^{ROUTE_BASE_URL}/local-file\?path=[^/]+"))
@make_real_path_router
@log_router_err()
async def _(url: "URL", **_):
    return Path(url.query["path"]).resolve()


@filters
def markdown(value: str) -> Markup:
    return Markup(md.render(value))  # noqa: S704


@filters
def layout(value: str, is_md: bool = False):
    if is_md:
        return markdown(value)

    if "<ft" in value and "</ft>" in value:
        with warning_suppress("Failed to parse PicMenu format rich text"):
            txt = transform_ft(value)
            return Markup(space(br(txt)))  # noqa: S704

    return safe_layout(value)


def register_filters(env: "jj.Environment"):
    env.filters.update(filters.data)

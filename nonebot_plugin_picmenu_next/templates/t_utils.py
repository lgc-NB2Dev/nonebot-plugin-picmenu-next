from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cookit.jinja import cookit_global_filter
from cookit.jinja.filters import br, safe_layout, space
from cookit.loguru import warning_suppress
from markdown_it import MarkdownIt
from markdown_katex import tex2html
from markupsafe import Markup
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.tasklists import tasklists_plugin
from nonebot_plugin_htmlrender.backend import build_backend
from nonebot_plugin_htmlrender.render import Render, get_default_render
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from ..ft_parser import transform_ft

if TYPE_CHECKING:
    from collections.abc import Collection

    import jinja2 as jj
    from nonebot_plugin_htmlrender.consts import RenderBackend

_render_cache: dict["RenderBackend", Render] = {}


def read_local_file(path: str | Path) -> str:
    return Path(path).expanduser().resolve().read_text("u8")


def get_template_render(
    backend: "RenderBackend | None",
    supported: "Collection[RenderBackend]",
    name: str,
) -> Render:
    if backend is None:
        render = get_default_render()
        actual = render.backend.backend
    else:
        render = None
        actual = backend
    if actual in supported:
        if render:
            return render
        if actual not in _render_cache:
            _render_cache[actual] = Render(backend=build_backend(actual))
        return _render_cache[actual]

    supported_text = ", ".join(x.value for x in supported) or "none"
    raise RuntimeError(
        f"{name} does not support htmlrender backend `{actual.value}`. "
        f"Supported backends: {supported_text}."
    )


def highlight_code(code: str, name: str, _attrs: Any):
    if name:
        with warning_suppress(f"Failed to highlight code, lang: {name}"):
            lexer = get_lexer_by_name(name)
            formatter = HtmlFormatter(nowrap=True)
            return highlight(code, lexer, formatter)
    return escape(code)


def render_math(content: str, options: dict[str, Any]) -> str:
    display_mode = bool(options.get("display_mode"))
    katex_options: dict[str, bool] = {"no-throw-on-error": True}
    if display_mode:
        katex_options["display-mode"] = True
    with warning_suppress("Failed to render LaTeX math with KaTeX"):
        return tex2html(content, katex_options)
    return escape(content)


md = (
    MarkdownIt("commonmark", {"highlight": highlight_code})
    .enable(["strikethrough", "linkify", "table"])
    .use(tasklists_plugin, enabled=True)
    .use(dollarmath_plugin, renderer=render_math)
)


filters = type(cookit_global_filter)(cookit_global_filter.data.copy())


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

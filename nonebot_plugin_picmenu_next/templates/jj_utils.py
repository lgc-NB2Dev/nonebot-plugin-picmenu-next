import mimetypes
from collections.abc import Callable
from html import escape
from pathlib import Path
from typing import Any, TypeAlias

from cookit import to_b64_url
from cookit.jinja import cookit_global_filter
from cookit.jinja.filters import br, safe_layout, space
from cookit.loguru import warning_suppress
from markdown_it import MarkdownIt
from markupsafe import Markup
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.tasklists import tasklists_plugin
from nonebot import get_plugin
from nonebot.plugin import Plugin
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from ..data_source.models import PMNPluginInfo
from ..ft_parser import transform_ft


def highlight_code(code: str, name: str, _attrs: Any):
    if name:
        with warning_suppress(f"Failed to highlight code, lang: {name}"):
            lexer = get_lexer_by_name(name)
            formatter = HtmlFormatter(nowrap=True)
            return highlight(code, lexer, formatter)
    return escape(code)


def render_math_script(content: str, options: dict[str, Any]) -> str:
    math_type = "math/tex"
    if options.get("display_mode"):
        math_type += "; mode=display"
    return f'<script type="{math_type}">{escape(content)}</script>'


LocalFileProcessor: TypeAlias = Callable[[PMNPluginInfo, str], str]
PluginSelfPathTransformer: TypeAlias = Callable[[PMNPluginInfo, Plugin, str], str]


def nothing_plugin_self_path_transformer(
    _info: PMNPluginInfo, _plugin: Plugin, path: str
) -> str:
    return path


def b64_plugin_self_path_transformer(
    _info: PMNPluginInfo, plugin: Plugin, path: str
) -> str:
    mime, _ = mimetypes.guess_type(path)
    return to_b64_url(Path(plugin.module.__path__[0]).joinpath(path).read_bytes(), mime)


def construct_default_local_file_processor(
    plugin_self_path_transformer: PluginSelfPathTransformer = nothing_plugin_self_path_transformer,
):
    def _local_file_processor(info: PMNPluginInfo, path: str) -> str:
        if (
            path.startswith("self:")
            and info.plugin_id
            and (plugin := get_plugin(info.plugin_id))
        ):
            return plugin_self_path_transformer(info, plugin, path[5:])
        return path

    return _local_file_processor


def new_markdown_it(
    local_file_processor: LocalFileProcessor | None = None,
):
    _ = local_file_processor
    return (
        MarkdownIt("commonmark", {"highlight": highlight_code})
        .enable(["strikethrough", "linkify", "table"])
        .use(tasklists_plugin, enabled=True)
        .use(dollarmath_plugin, renderer=render_math_script)
    )


def setup_base_filters(
    local_file_processor: LocalFileProcessor | None = None,
):
    filters = type(cookit_global_filter)(cookit_global_filter.data.copy())

    md = new_markdown_it(local_file_processor)

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

    return filters

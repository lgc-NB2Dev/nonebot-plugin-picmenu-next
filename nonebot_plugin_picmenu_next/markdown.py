import re
from collections.abc import Callable
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeAlias, cast
from typing_extensions import NotRequired, TypedDict

from cookit import to_b64_url
from cookit.loguru import warning_suppress
from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.tasklists import tasklists_plugin
from nonebot import get_plugin
from nonebot.plugin import Plugin
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from .data_source.models import PMNPluginInfo

if TYPE_CHECKING:
    from markdown_it.renderer import RendererHTML
    from markdown_it.token import Token
    from markdown_it.utils import EnvType, OptionsDict


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


PluginResPathProcessor: TypeAlias = Callable[[PMNPluginInfo, str], str]
PluginResPathTransformer: TypeAlias = Callable[[str, Path, PMNPluginInfo, Plugin], str]


def b64_prp_transformer(
    path: str, module_path: Path, _info: PMNPluginInfo, _plugin: Plugin
) -> str:
    import mimetypes

    mime, _ = mimetypes.guess_type(path)
    return to_b64_url(module_path.joinpath(path).read_bytes(), mime)


def build_default_prp_processor(
    prp_transformer: PluginResPathTransformer,
):
    def _prp_processor(info: PMNPluginInfo, path: str) -> str:
        if not (path.startswith("plugin:") and info.plugin_id):
            return path
        rest = path[7:]
        comma_idx = rest.find(",")
        if comma_idx < 0:
            return path
        plugin_key = rest[:comma_idx]
        rel_path = rest[comma_idx + 1 :]
        plugin_id = info.plugin_id if plugin_key == "self" else plugin_key
        if not (plugin := get_plugin(plugin_id)):
            return path
        return prp_transformer(rel_path, Path(plugin.module.__path__[0]), info, plugin)

    return _prp_processor


class PluginResPathProcessPluginEnv(TypedDict):
    info: NotRequired[PMNPluginInfo | None]
    prp_processor: NotRequired[PluginResPathProcessor | None]


_HTML_ATTR_RE = re.compile(r"""\b(src|href|poster)\s*=\s*["']plugin:([^"'\s]+)["']""")


def _resolve_attr(
    token: "Token", attr_name: str, env: PluginResPathProcessPluginEnv
) -> None:
    val = token.attrGet(attr_name)
    if val and isinstance(val, str):
        prp = env.get("prp_processor")
        info = env.get("info")
        if prp and info:
            token.attrSet(attr_name, prp(info, val))


def _resolve_html_content(content: str, env: PluginResPathProcessPluginEnv) -> str:
    prp = env.get("prp_processor")
    info = env.get("info")
    if not (prp and info):
        return content

    def _repl(m: re.Match[str]) -> str:
        return f'{m.group(1)}="{prp(info, f"plugin:{m.group(2)}")}"'

    return _HTML_ATTR_RE.sub(_repl, content)


def resource_resolve_plugin(md: MarkdownIt):
    """将 markdown 中 image/link/html 的 plugin: 路径转为实际 URL。"""

    renderer = cast("RendererHTML", md.renderer)
    rules = cast(
        "dict[str, Callable[[list[Token], int, OptionsDict, EnvType], str]]",
        renderer.rules,
    )

    default_image = rules["image"]

    def _image(
        tokens: "list[Token]",
        idx: int,
        options: "OptionsDict",
        env: "EnvType",
    ) -> str:
        _resolve_attr(tokens[idx], "src", cast("PluginResPathProcessPluginEnv", env))
        return default_image(tokens, idx, options, env)

    # link_open walks renderToken fallback, hook to resolve href first
    default_render_token = renderer.renderToken

    def _link_open(
        tokens: "list[Token]",
        idx: int,
        options: "OptionsDict",
        env: "EnvType",
    ) -> str:
        _resolve_attr(tokens[idx], "href", cast("PluginResPathProcessPluginEnv", env))
        return default_render_token(tokens, idx, options, env)

    default_html_block = rules["html_block"]
    default_html_inline = rules["html_inline"]

    def _html_block(
        tokens: "list[Token]",
        idx: int,
        options: "OptionsDict",
        env: "EnvType",
    ) -> str:
        content = tokens[idx].content
        resolved = _resolve_html_content(
            content, cast("PluginResPathProcessPluginEnv", env)
        )
        if resolved != content:
            return resolved

        return default_html_block(tokens, idx, options, env)

    def _html_inline(
        tokens: "list[Token]",
        idx: int,
        options: "OptionsDict",
        env: "EnvType",
    ) -> str:
        content = tokens[idx].content
        resolved = _resolve_html_content(
            content, cast("PluginResPathProcessPluginEnv", env)
        )
        if resolved != content:
            return resolved

        return default_html_inline(tokens, idx, options, env)

    rules["image"] = _image
    rules["link_open"] = _link_open
    rules["html_block"] = _html_block
    rules["html_inline"] = _html_inline


md = (
    MarkdownIt("commonmark", {"highlight": highlight_code})
    .enable(["strikethrough", "linkify", "table"])
    .use(tasklists_plugin, enabled=True)
    .use(dollarmath_plugin, renderer=render_math_script)
    .use(resource_resolve_plugin)
)

"""Make sure `require("nonebot_plugin_htmlrender")` before importing this module."""

from collections.abc import Collection
from pathlib import Path
from typing import TYPE_CHECKING

import nonebot_plugin_htmlrender
from nonebot import get_driver
from nonebot_plugin_htmlrender.backend import build_backend
from nonebot_plugin_htmlrender.render import Render, get_default_render

if TYPE_CHECKING:
    from nonebot_plugin_htmlrender.consts import RenderBackend


HTMLRENDER_DIR = Path(nonebot_plugin_htmlrender.__path__[0])
HTMLRENDER_MD_TEMPLATE_DIR = HTMLRENDER_DIR / "templates" / "markdown"

driver = get_driver()

_render_cache: dict["RenderBackend", Render] = {}


def get_template_render(
    backend: "RenderBackend | None",
    supported: Collection["RenderBackend"],
    name: str | None = None,
    fallback_backend: "RenderBackend | None" = None,
) -> tuple[Render, "RenderBackend"]:
    if backend is None:
        try:
            render = get_default_render()
            actual = render.backend.backend
        except RuntimeError:
            if fallback_backend is None:
                raise
            render = None
            actual = fallback_backend
    else:
        render = None
        actual = backend
    if actual in supported:
        if render:
            return render, actual
        if actual not in _render_cache:
            _render_cache[actual] = Render(backend=build_backend(actual))
        return _render_cache[actual], actual
    if (
        backend is None
        and fallback_backend is not None
        and fallback_backend in supported
    ):
        actual = fallback_backend
        if actual not in _render_cache:
            _render_cache[actual] = Render(backend=build_backend(actual))
        return _render_cache[actual], actual

    supported_text = ", ".join(x.value for x in supported) or "none"
    raise RuntimeError(
        f"{name or 'Current template'} does not support htmlrender backend `{actual.value}`. "
        f"Supported backends: {supported_text}."
    )


async def shutdown_template_renders() -> None:
    cached_renders = tuple(_render_cache.values())
    _render_cache.clear()
    for render in cached_renders:
        await render.shutdown_render()


@driver.on_shutdown
async def _():
    await shutdown_template_renders()

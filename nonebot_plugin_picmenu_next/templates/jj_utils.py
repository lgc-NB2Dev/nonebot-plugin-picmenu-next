from typing import Any, cast

from cookit.jinja import cookit_global_filter
from cookit.jinja.filters import br, safe_layout, space
from cookit.loguru import warning_suppress
from markupsafe import Markup

from ..data_source.models import PMNPluginInfo
from ..ft_parser import transform_ft
from ..markdown import PluginResPathProcessor, PluginResPathProcessPluginEnv, md

filters = type(cookit_global_filter)(cookit_global_filter.data.copy())


def build_base_render_kwargs(
    info: PMNPluginInfo | None = None,
    prp_processor: PluginResPathProcessor | None = None,
):
    from ..config import version

    def markdown(value: str) -> Markup:
        env: PluginResPathProcessPluginEnv = {
            "info": info,
            "prp_processor": prp_processor,
        }
        return Markup(  # noqa: S704
            md.render(value, env=cast("Any", env))
        )

    def layout(value: str, is_md: bool = False):
        if is_md:
            return markdown(value)

        if "<ft" in value and "</ft>" in value:
            with warning_suppress("Failed to parse PicMenu format rich text"):
                txt = transform_ft(value)
                return Markup(space(br(txt)))  # noqa: S704

        return safe_layout(value)

    return {
        "layout": layout,
        "markdown": markdown,
        "version": version(),
    }

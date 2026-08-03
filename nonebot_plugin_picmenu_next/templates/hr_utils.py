"""Make sure `require("nonebot_plugin_htmlrender")` before importing this module."""

from pathlib import Path

import nonebot_plugin_htmlrender

_HTMLRENDER_DIR = Path(nonebot_plugin_htmlrender.__path__[0])
for _katex_dir in (
    _HTMLRENDER_DIR / "templates" / "katex",
    _HTMLRENDER_DIR / "templates" / "markdown" / "katex",
):
    if _katex_dir.is_dir():
        HTMLRENDER_KATEX_DIR = _katex_dir
        break
else:
    raise RuntimeError("Could not find htmlrender KaTeX template resources.")

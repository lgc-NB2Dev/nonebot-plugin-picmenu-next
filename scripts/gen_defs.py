# ruff: noqa: INP001, E402

import json
from pathlib import Path

import nonebot

nonebot.init(localstore_use_cwd=True)

nonebot.require("nonebot_plugin_picmenu_next")

from nonebot_plugin_picmenu_next.data_source import models

(Path(__file__).parent.parent / "defs" / "ExternalPluginInfo.json").write_text(
    json.dumps(
        models.ExternalPluginInfo.model_json_schema(),
        ensure_ascii=False,
    ),
    "u8",
)

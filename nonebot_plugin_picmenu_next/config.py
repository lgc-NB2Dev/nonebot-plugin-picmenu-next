from pathlib import Path

from cookit.nonebot.localstore import ensure_localstore_path_config
from cookit.pyd import model_with_alias_generator
from nonebot import get_plugin_config
from nonebot_plugin_localstore import get_plugin_config_dir
from pydantic import BaseModel

ensure_localstore_path_config()

config_dir = get_plugin_config_dir()

pm_menus_dir = Path.cwd() / "menu_config/menus"
external_infos_dir = config_dir / "external_infos"
external_infos_dir.mkdir(parents=True, exist_ok=True)


@model_with_alias_generator(lambda x: f"pmn_{x}")
class ConfigModel(BaseModel):
    index_template: str = "default"
    detail_template: str = "default"
    func_detail_template: str = "default"
    only_superuser_see_hidden: bool = False


config: ConfigModel = get_plugin_config(ConfigModel)


def version():
    from . import __version__

    return __version__

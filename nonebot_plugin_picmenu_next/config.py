from cookit.pyd import model_with_alias_generator
from nonebot import get_plugin_config
from pydantic import BaseModel


@model_with_alias_generator(lambda x: f"pmn_{x}")
class ConfigModel(BaseModel):
    index_template: str = "default"
    detail_template: str = "default"
    func_detail_template: str = "default"


config: ConfigModel = get_plugin_config(ConfigModel)

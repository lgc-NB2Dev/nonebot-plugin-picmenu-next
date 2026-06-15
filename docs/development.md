<!-- markdownlint-disable MD031 -->

# 开发文档

## Quick QA

### 来到这里只想看如何适配 Markdown 展示？

很简单！按如下方式编辑插件元数据，你即刻就可让插件信息走 Markdown 渲染：

```python
__plugin_meta__ = PluginMetadata(
    ...,
    extra={
        # ...
        "pmn": {  # PicMenu Next 专有配置字段，详见下方文档
            "markdown": True,  # 开启 PicMenu Next 的 Markdown 支持
        },
        # ...
    },
)
```

## 编写外部菜单项

本插件会读取以下目录中的所有 `json` / `yml(yaml)` / `toml` 文件并作为外部菜单配置加载

- 插件 localstore 路径下的 `external_infos` 文件夹
- 原 PicMenu 的 `menu_config/menus` 文件夹

插件会将其文件名作为 `插件 ID` (如为顶层级插件，通常为插件包名) 来判断是否覆盖已存在的插件的菜单信息  
仅被配置文件定义的顶层属性会被覆盖

配置文件定义 Schema 请查看 [defs/ExternalPluginInfo.json](../defs/ExternalPluginInfo.json)，可以使用以下语法引入你的配置文件：

- JSON:
  ```json
  {
    "$schema": "https://raw.githubusercontent.com/lgc-NB2Dev/nonebot-plugin-picmenu-next/refs/heads/master/defs/ExternalPluginInfo.json"
  }
  ```
- YAML（使用 VSCode YAML 扩展）:
  ```yaml
  # yaml-language-server: $schema=https://raw.githubusercontent.com/lgc-NB2Dev/nonebot-plugin-picmenu-next/refs/heads/master/defs/ExternalPluginInfo.json
  ```
- TOML（使用 VSCode Even Better TOML 扩展）:
  ```toml
  #:schema https://raw.githubusercontent.com/lgc-NB2Dev/nonebot-plugin-picmenu-next/refs/heads/master/defs/ExternalPluginInfo.json
  ```

## 插件开发者对接

PicMenu Next 的数据声明格式派生自 [nonebot_plugin_PicMenu](https://github.com/hamo-reid/nonebot_plugin_PicMenu)，保留了 `menu_data`、`func`、`trigger_method`、`trigger_condition`、`brief_des`、`detail_des` 等字段。PicMenu Next 会优先读取插件的 `PluginMetadata`，并从 `extra` 字段中解析扩展信息。

```python
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="示例插件",
    description="插件简介，支持 Markdown 时会按 Markdown 渲染",
    usage="插件用法说明",
    type="application",
    extra={
        "author": "LgCookie",
        "version": "1.0.0",
        "pmn": {
            "hidden": False,
            "markdown": True,
            "template": "default",
        },
        "menu_data": [
            {
                "func": "功能名称",
                "trigger_method": "`/example`",
                "trigger_condition": "触发条件说明",
                "brief_des": "简要介绍",
                "detail_des": "详细用法，开启 markdown 后可写 **Markdown** 与 $E=mc^2$",
            }
        ],
    },
)
```

`pmn` 支持以下可选字段：

| 字段       | 类型          | 默认值  | 说明                                       |
| ---------- | ------------- | ------- | ------------------------------------------ |
| `hidden`   | `bool`        | `False` | 是否在普通帮助菜单中隐藏                   |
| `markdown` | `bool`        | `False` | 是否将描述、用法、功能详情按 Markdown 渲染 |
| `template` | `str \| None` | `None`  | 为该插件指定详情页模板                     |

`menu_data` 中每一项对应一个三级菜单功能，必填字段为 `func`、`trigger_method`、`trigger_condition`、`brief_des`、`detail_des`。

每个功能项还可以额外设置：

| 字段           | 类型          | 默认值  | 说明                       |
| -------------- | ------------- | ------- | -------------------------- |
| `pmn_hidden`   | `bool`        | `False` | 是否隐藏该功能             |
| `pmn_template` | `str \| None` | `None`  | 为该功能指定功能详情页模板 |

## Mixin 编写

Mixin 用于在 PicMenu Next 收集或展示菜单前后修改菜单数据。所有 mixin 都是异步函数，返回修改后的数据。

常用入口位于 `nonebot_plugin_picmenu_next.data_source.mixin`：

| 装饰器                  | 作用范围                         |
| ----------------------- | -------------------------------- |
| `plugin_collect_mixins` | 插件信息收集完成后，全局修改列表 |
| `plugin_mixins`         | 首页渲染前，全局修改插件列表     |
| `self_mixins`           | 首页渲染前，只修改当前插件自身   |
| `plugin_detail_mixins`  | 详情页渲染前，全局修改插件信息   |
| `self_detail_mixins`    | 详情页渲染前，只修改当前插件自身 |

`priority` 数字越小越早执行。mixin 函数第一个参数是 `next_mixin`，可以选择在调用前或调用后修改数据。

> [!WARNING]
> 传入 mixin 的 `PMNPluginInfo` / `PMDataItem` 是当前菜单数据中的**现有对象引用**，直接修改字段是预期行为，后续 mixin 与模板会看到这些修改。  
> 如果只想临时派生一份数据，请在 mixin 内自行复制对象后再返回。

```python
from nonebot_plugin_picmenu_next.data_source.mixin import (
    PluginDetailMixinNext,
    SelfMixinNext,
    self_detail_mixins,
    self_mixins,
)
from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo


@self_mixins(priority=5)
async def add_suffix(
    next_mixin: SelfMixinNext,
    info: PMNPluginInfo,
) -> PMNPluginInfo:
    info = await next_mixin(info)
    info.description = f"{info.description or ''}\n\n由当前插件的 mixin 追加。"
    return info


@self_detail_mixins(priority=5)
async def add_detail_note(
    next_mixin: PluginDetailMixinNext,
    info: PMNPluginInfo,
) -> PMNPluginInfo:
    info = await next_mixin(info)
    info.usage = f"{info.usage or ''}\n\n> 这段内容只会出现在当前插件详情页。"
    return info
```

全局修改示例：

```python
from nonebot_plugin_picmenu_next.data_source.mixin import PluginMixinNext, plugin_mixins
from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo


@plugin_mixins(priority=10)
async def sort_by_name(
    next_mixin: PluginMixinNext,
    infos: list[PMNPluginInfo],
) -> list[PMNPluginInfo]:
    infos = await next_mixin(infos)
    return sorted(infos, key=lambda x: x.name.casefold())
```

## 菜单模板

菜单模板通过装饰器注册，输入 PicMenu Next 已收集好的数据，输出 `UniMessage`。

```python
from nonebot_plugin_alconna.uniseg import UniMessage
from nonebot_plugin_picmenu_next.data_source.models import PMDataItem, PMNPluginInfo
from nonebot_plugin_picmenu_next.templates import (
    detail_templates,
    func_detail_templates,
    index_templates,
)


@index_templates("plain")
async def render_index(
    infos: list[PMNPluginInfo],
    showing_hidden: bool,
) -> UniMessage:
    text = "\n".join(f"{i}. {info.name}" for i, info in enumerate(infos, 1))
    return UniMessage.text(text)


@detail_templates("plain")
async def render_detail(
    info: PMNPluginInfo,
    info_index: int,
    showing_hidden: bool,
) -> UniMessage:
    return UniMessage.text(f"{info.name}\n\n{info.description or ''}")


@func_detail_templates("plain")
async def render_func_detail(
    info: PMNPluginInfo,
    info_index: int,
    func: PMDataItem,
    func_index: int,
    showing_hidden: bool,
) -> UniMessage:
    return UniMessage.text(f"{info.name} > {func.func}\n\n{func.detail_des}")
```

三个模板注册器互相独立，通常建议使用同一个模板名分别注册首页、插件详情页、功能详情页。用户可通过 `PMN_INDEX_TEMPLATE`、`PMN_DETAIL_TEMPLATE`、`PMN_FUNC_DETAIL_TEMPLATE` 设置默认模板。

单个插件也可以通过 `extra["pmn"]["template"]` 指定详情页模板，单个功能可以通过 `pmn_template` 指定功能详情页模板。

模板实现本身是黑盒接口：可以输出图片，也可以输出文字；可以使用 htmlrender，也可以使用其它渲染方式。若模板依赖特定渲染后端，应在模板实现内部自行检查并抛出清晰错误。

<!-- markdownlint-disable MD031 -->

# 开发文档

## Quick QA

### 如何适配 Markdown 展示？

按如下方式编辑插件元数据，你即刻就可让插件信息走 Markdown 渲染：

```python
__plugin_meta__ = PluginMetadata(
    ...,
    extra={
        "pmn": {  # PicMenu Next 专有配置字段，详见下方文档
            "markdown": True,  # 开启 PicMenu Next 的 Markdown 支持
        },
    },
)
```

### 如何禁用 Alconna 命令自动探测？

在插件元数据的 `extra` 中显式设置 `menu_data`，例如空列表 `[]`，即可表示插件已自行声明三级菜单，PicMenu Next 不会再从该插件注册的 Alconna 命令自动补全：

```python
__plugin_meta__ = PluginMetadata(
    ...,
    extra={
        "menu_data": [],
    },
)
```

### 已经写了菜单项，还想附加 Alconna 自动探测结果？

在 `extra["pmn"]` 中设置 `alc_force_enable_detect=True` 即可强制启用 Alconna 自动探测。探测生成的功能项会附加到当前插件菜单项的最前面：

```python
__plugin_meta__ = PluginMetadata(
    ...,
    extra={
        "pmn": {
            "alc_force_enable_detect": True,
        },
        "menu_data": [
            # ...
        ],
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
            "alc_force_enable_detect": False,
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

| 字段                      | 类型          | 默认值  | 说明                                                |
| ------------------------- | ------------- | ------- | --------------------------------------------------- |
| `hidden`                  | `bool`        | `False` | 是否在普通帮助菜单中隐藏                            |
| `markdown`                | `bool`        | `False` | 是否将描述、用法、功能详情按 Markdown 渲染          |
| `template`                | `str \| None` | `None`  | 为该插件指定详情页模板                              |
| `alc_force_enable_detect` | `bool`        | `False` | 即使已定义 `menu_data`，也强制启用 Alconna 自动探测 |

`menu_data` 中每一项对应一个三级菜单功能，必填字段为 `func`、`trigger_method`、`trigger_condition`、`brief_des`、`detail_des`。

每个功能项还可以额外设置：

| 字段           | 类型          | 默认值  | 说明                       |
| -------------- | ------------- | ------- | -------------------------- |
| `pmn_hidden`   | `bool`        | `False` | 是否隐藏该功能             |
| `pmn_template` | `str \| None` | `None`  | 为该功能指定功能详情页模板 |

## Alconna 命令自动探测

如果插件没有提供 `menu_data` 或将其设为 `None`，PicMenu Next 会尝试从该插件注册的 Alconna 命令自动补全三级菜单。若插件 metadata 中提供了 `menu_data` 且值不是 `None`，包括显式设为空列表 `[]`，都会视为插件已自行声明三级菜单并禁用 Alconna 自动探测。

如果你既想保留手写菜单项，又想附加自动探测结果，可以在插件 metadata 的 `extra["pmn"]` 中设置 `alc_force_enable_detect=True`。开启后即使 `menu_data` 已经有内容，PicMenu Next 也会继续探测该插件的 Alconna 命令，并将生成的菜单项放到现有菜单项最前面。

如果你需要更复杂的追加、删除或重排逻辑，可以通过 mixin 在菜单数据收集后修改 `PMNPluginInfo.pm_data`。

自动探测会读取命令名、可触发命令、命令描述与帮助文本生成 `PMDataItem`。其中 `brief_des` 固定使用 `CommandMeta.description`；如果插件启用了 `extra["pmn"]["markdown"] = True`，并且命令没有自定义 formatter，详细用法会使用 Alconna 的 Markdown formatter 生成。

单条 Alconna 命令可以通过 `CommandMeta.extra["pmn"]` 覆盖自动生成的菜单项字段。该配置按全可空的 `PMDataItem` 校验，未填写的字段继续使用自动生成值：

```python
from arclet.alconna import Alconna, CommandMeta

alc = Alconna(
    "example",
    meta=CommandMeta(
        description="简要说明",
        extra={
            "pmn": {
                "func": "功能名称",
                "trigger_method": "`/example`",
                "trigger_condition": "发送对应指令",
                "detail_des": "详细用法说明",
                "pmn_hidden": False,
                "pmn_template": "default",
            },
        },
    ),
)
```

## Mixin 编写

Mixin 用于在 PicMenu Next 收集或展示菜单前后修改菜单数据。所有 mixin 都是异步函数，返回修改后的数据。

常用入口位于 `nonebot_plugin_picmenu_next.data_source.mixin`：

| 装饰器                  | 作用范围                             |
| ----------------------- | ------------------------------------ |
| `plugin_collect_mixins` | 插件信息收集完成后，全局修改列表     |
| `plugin_mixins`         | 首页渲染前，全局修改插件列表         |
| `self_mixins`           | 首页渲染前，只修改当前插件自身       |
| `plugin_detail_mixins`  | 功能详情页渲染前，全局修改插件信息   |
| `self_detail_mixins`    | 功能详情页渲染前，只修改当前插件自身 |

`priority` 数字越小越早执行。mixin 函数第一个参数是 `next_mixin`，它不一定要放在函数最后调用；可以按需放在任意位置，以决定你的逻辑在其他 mixin 执行完成之前、之后或前后都运行。

如果某个 mixin 执行时抛出异常，PicMenu Next 会记录一条警告并跳过当前 mixin，然后继续调用后续 mixin。这样可以避免单个扩展导致帮助菜单整体不可用；如果你的 mixin 已经在抛错前原地修改了对象，这些修改不会被自动回滚。

> [!CAUTION]
> 传入 mixin 的 `PMNPluginInfo` / `PMDataItem` 是当前菜单数据中的**现有对象引用**
>
> 直接修改字段会同步写回内存中的全局插件数据，这是预期行为，也意味着这个改动**会污染后续每一次调用**  
> 例如每次处理帮助菜单时都追加 `description`，文本会在之后的每次调用中持续累积。
>
> 除非你确实想永久修改这份全局数据，否则请先复制原数据，或新建一份数据后再修改并返回。

```python
from nonebot_plugin_picmenu_next.data_source.mixin import (
    PluginCollectMixinNext,
    PluginDetailMixinNext,
    PluginMixinNext,
    SelfMixinNext,
    plugin_collect_mixins,
    plugin_detail_mixins,
    plugin_mixins,
    self_detail_mixins,
    self_mixins,
)
from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo


# plugin_collect_mixins 在插件信息收集完成后运行，传入收集好的所有插件信息
# 示例中添加一个虚拟插件，并修改它的展示信息
@plugin_collect_mixins()
async def _(next_mixin: PluginCollectMixinNext, infos: list[PMNPluginInfo]):
    infos.append(
        PMNPluginInfo(
            plugin_id="picmenu_mixin_test",
            name="插件收集 Mixin 测试",
            description="我是在插件收集阶段被 Mixin 添加的插件！",
        ),
    )
    idx = next(i for i, x in enumerate(infos) if x.plugin_id == "picmenu_mixin_test")

    info = infos[idx].model_copy()
    info.name = "PicMenu Mixin 测试"
    info.description = "我的名称与简介是在插件收集阶段被 Mixin 修改的！"
    infos[idx] = info
    return await next_mixin(infos)


# self_mixins 在帮助首页渲染前运行，但只会传入当前插件自身的信息
# 示例修改了当前插件的展示信息
@self_mixins()
async def _(next_mixin: SelfMixinNext, info: PMNPluginInfo):
    info = info.model_copy()  # 注意上方 Caution
    info.description = f"{info.description or ''} 我被 Mixin 修改了！"
    return await next_mixin(info)


# plugin_mixins 在帮助首页渲染前运行，传入所有插件信息
# 示例中调整了 alconna 插件的展示信息
@plugin_mixins()
async def _(next_mixin: PluginMixinNext, infos: list[PMNPluginInfo]):
    idx = next(
        i for i, x in enumerate(infos) if x.plugin_id == "nonebot_plugin_alconna"
    )
    info = infos[idx].model_copy()  # 注意上方 Caution
    info.description = f"{info.description or ''} 我被 Mixin 修改了！"
    infos[idx] = info
    return await next_mixin(infos)


# plugin_detail_mixins 在功能详情页渲染前运行，传入当前正在查看的插件信息
# 示例中给所有插件的功能详情页用法追加一段提示
@plugin_detail_mixins()
async def _(next_mixin: PluginDetailMixinNext, info: PMNPluginInfo):
    info = info.model_copy()  # 注意上方 Caution
    info.usage = f"{info.usage or ''}\n\n> 这段内容会出现在所有插件功能详情页。"
    return await next_mixin(info)


# self_detail_mixins 在功能详情页渲染前运行，但只会传入当前插件自身的信息
# 示例中给当前插件的功能详情页简介追加一段提示
@self_detail_mixins()
async def _(next_mixin: PluginDetailMixinNext, info: PMNPluginInfo):
    info = info.model_copy()  # 注意上方 Caution
    info.description = f"{info.description or ''}\n\n这段内容只会出现在当前插件功能详情页。"
    return await next_mixin(info)
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

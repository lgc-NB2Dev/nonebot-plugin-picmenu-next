<!-- markdownlint-disable MD031 MD033 MD036 MD041 -->

<div align="center">

<a href="https://v2.nonebot.dev/store">
  <img src="https://raw.githubusercontent.com/A-kirami/nonebot-plugin-template/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo">
</a>

<p>
  <img src="https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/template/plugin.svg" alt="NoneBotPluginText">
</p>

# NoneBot-Plugin-PicMenu-Next

_✨ 新一代的图片帮助插件 ✨_

<img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="python">
<a href="https://pdm.fming.dev">
  <img src="https://img.shields.io/badge/pdm-managed-blueviolet" alt="pdm-managed">
</a>
<a href="https://wakatime.com/badge/user/b61b0f9a-f40b-4c82-bc51-0a75c67bfccf/project/08822e56-b8a3-4a4e-a8dd-7d95757e3803">
  <img src="https://wakatime.com/badge/user/b61b0f9a-f40b-4c82-bc51-0a75c67bfccf/project/08822e56-b8a3-4a4e-a8dd-7d95757e3803.svg" alt="wakatime">
</a>

<br />

<a href="https://pydantic.dev">
  <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/template/pyd-v1-or-v2.json" alt="Pydantic Version 1 Or 2" >
</a>
<a href="./LICENSE">
  <img src="https://img.shields.io/github/license/lgc-NB2Dev/nonebot-plugin-picmenu-next.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-picmenu-next">
  <img src="https://img.shields.io/pypi/v/nonebot-plugin-picmenu-next.svg" alt="pypi">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-picmenu-next">
  <img src="https://img.shields.io/pypi/dm/nonebot-plugin-picmenu-next" alt="pypi download">
</a>

<br />

<a href="https://registry.nonebot.dev/plugin/nonebot-plugin-picmenu-next:nonebot_plugin_picmenu_next">
  <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fnbbdg.lgc2333.top%2Fplugin%2Fnonebot-plugin-picmenu-next" alt="NoneBot Registry">
</a>
<a href="https://registry.nonebot.dev/plugin/nonebot-plugin-picmenu-next:nonebot_plugin_picmenu_next">
  <img src="https://img.shields.io/endpoint?url=https%3A%2F%2Fnbbdg.lgc2333.top%2Fplugin-adapters%2Fnonebot-plugin-picmenu-next" alt="Supported Adapters">
</a>

</div>

## 📖 介绍

- ✨ **美观的图片界面**：直观友好的图片界面
- 🛠️ **PicMenu 兼容**：本插件使用 PicMenu 插件格式的三级菜单（功能详情），兼容 PicMenu 的 `<ft>` 富文本标签（但不太推荐使用）
- 🔍 **支持模糊搜索**：支持通过序号或名称查找插件及功能，并提供插件名称的模糊匹配
- 🔤 **拼音支持**：插件排序与模糊搜索时考虑拼音，提高中文环境下的使用体验
- 📜 **Markdown 支持**：支持 Markdown 格式的帮助信息展示（需要插件开发者主动适配）
- 🔒 **隐藏控制**：默认状态下类型为 `library` 的插件会对普通用户隐藏
- 🎨 **自定义模板**：提供模板开发者注册模板的接口，提供插件开发者自定义某插件使用的详细信息模板的方式，提供配置供用户自定义想要使用的模板
- 🔌 **插件扩展机制**：提供强大的 mixin 支持，允许插件通过中间件方式自定义帮助菜单展示和行为

### 展示图

<details>
<summary>主页面</summary>

![亮色主页](https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/picmenu-next/light_main.jpg)  
![暗色主页](https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/picmenu-next/dark_main.jpg)

</details>

<details>
<summary>插件详情</summary>

![亮色插件详情](https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/picmenu-next/light_detail.jpg)  
![暗色插件详情](https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/picmenu-next/dark_detail.jpg)

</details>

<details>
<summary>插件详情（带功能详情三级菜单）</summary>

![亮色带三级菜单插件详情](https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/picmenu-next/light_with_func.jpg)  
![暗色带三级菜单插件详情](https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/picmenu-next/dark_with_func.jpg)

</details>

<details>
<summary>功能详情</summary>

![亮色功能详情](https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/picmenu-next/light_func_detail.jpg)  
![暗色功能详情](https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/picmenu-next/dark_func_detail.jpg)

</details>

<details>
<summary>Markdown 测试</summary>

![亮色 Markdown 测试](https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/picmenu-next/light_markdown.jpg)  
![暗色 Markdown 测试](https://raw.githubusercontent.com/lgc-NB2Dev/readme/main/picmenu-next/dark_markdown.jpg)

</details>

## 💿 安装

以下提到的方法 任选**其一** 即可

<details open>
<summary>[推荐] 使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

```bash
nb plugin install nonebot-plugin-picmenu-next
```

</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

```bash
pip install nonebot-plugin-picmenu-next
```

</details>
<details>
<summary>pdm</summary>

```bash
pdm add nonebot-plugin-picmenu-next
```

</details>
<details>
<summary>poetry</summary>

```bash
poetry add nonebot-plugin-picmenu-next
```

</details>
<details>
<summary>conda</summary>

```bash
conda install nonebot-plugin-picmenu-next
```

</details>

打开 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分的 `plugins` 项里追加写入

```toml
[tool.nonebot]
plugins = [
    # ...
    "nonebot_plugin_picmenu_next"
]
```

</details>

## ⚙️ 配置

在 NoneBot2 项目的 `.env` 文件中添加下表中的配置

|             配置项              | 必填 |  默认值   |              说明              |
| :-----------------------------: | :--: | :-------: | :----------------------------: |
|      `PMN_INDEX_TEMPLATE`       |  否  | `default` |       首页展示模板的名称       |
|      `PMN_DETAIL_TEMPLATE`      |  否  | `default` |       插件详情模板的名称       |
|   `PMN_FUNC_DETAIL_TEMPLATE`    |  否  | `default` |     插件功能详情模板的名称     |
| `PMN_ONLY_SUPERUSER_SEE_HIDDEN` |  否  |  `False`  | 是否仅超级用户可以查看隐藏内容 |

## 🎉 使用

发送 `帮助` 指令试试吧！

## 🔧 开发

文档待补充

## 📞 联系

QQ：3076823485  
Telegram：[@lgc2333](https://t.me/lgc2333)  
吹水群：[1105946125](https://jq.qq.com/?_wv=1027&k=Z3n1MpEp)  
邮箱：<lgc2333@126.com>

## 💡 鸣谢

### [hamo-reid/nonebot_plugin_PicMenu](https://github.com/hamo-reid/nonebot_plugin_PicMenu)

- 灵感来源（？）

## 💰 赞助

**[赞助我](https://blog.lgc2333.top/donate)**

感谢大家的赞助！你们的赞助将是我继续创作的动力！

## 📝 更新日志

### 0.1.1

- 尝试兼容 Pydantic V1

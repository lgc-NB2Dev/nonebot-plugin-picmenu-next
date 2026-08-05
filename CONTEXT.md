# PicMenu Next

PicMenu Next maintains the language for a NoneBot plugin help-menu context. These terms describe the user-facing help domain, not implementation details.

## Language

**帮助菜单聚合与渲染**:
The core responsibility of PicMenu Next: collecting help data and presenting it as help-menu views.

**帮助首页**:
The top-level help view that lists available plugins.
_Also_: 一级菜单

**普通帮助菜单**:
A menu view opened through a help-menu command.

**帮助命令**:
The public command that opens PicMenu help views and accepts menu queries. Its canonical name is `help`, with the Chinese aliases `帮助` and `菜单`.

**命令起始符**:
The runtime-configured prefix a user must place before a help command invocation.

**菜单查询**:
Input supplied by a user to locate a plugin or function item in a help menu.

**菜单排序**:
The deterministic display order of plugin menu items.

**菜单索引**:
The 1-based position of a menu item in the current sorted menu snapshot. It is not a stable identifier.

**同拼音菜单项**:
Plugin menu items with the same pinyin sort key.

**插件详情页**:
The help view for one plugin, showing its plugin-level description and its child help entries.
_Also_: 二级菜单

**功能详情页**:
The help view for one function item.
_Also_: 三级菜单

**插件菜单项**:
A plugin-level entry in PicMenu help, whether it comes from a loaded plugin or external menu config.

**菜单模板**:
A renderer for one kind of help-menu view.

**首页模板**:
A menu template for the help homepage.
_Also_: 一级菜单模板

**插件详情模板**:
A menu template for a plugin detail page.
_Also_: 二级菜单模板

**功能详情模板**:
A menu template for a function detail page.
_Also_: 三级菜单模板

**插件模板选择**:
The plugin-level setting that selects a menu template for plugin detail rendering and optional function-detail inheritance.
_Also_: `template`

**功能项模板选择**:
The function-item setting that selects a menu template for that function detail page.
_Also_: `pmn_template`

**功能模板继承开关**:
The plugin-level setting that decides whether function detail pages inherit the plugin template selection.
_Also_: `inherit_func_template`

**功能项**:
A help entry under a plugin menu item that describes one user-facing feature, including how it is triggered and what it does.
_Also_: 三级菜单项

**功能项名称**:
The user-facing name of a function item.
_Also_: `func`

**触发方式**:
The user-facing command or action used to invoke a function item.
_Also_: `trigger_method`

**触发条件**:
The circumstance under which a function item can be triggered.
_Also_: `trigger_condition`

**功能项简介**:
A short summary of a function item.
_Also_: `brief_des`

**功能项详情**:
The detailed help content for a function item.
_Also_: `detail_des`

**菜单数据**:
Help data collected for PicMenu rendering.

**功能项列表**:
The list of function items under a plugin menu entry.
_Also_: `menu_data`, `funcs`

**Alconna 自动探测**:
The process of discovering PicMenu help data from registered Alconna commands.

**自动探测功能项**:
A function item discovered from an existing command declaration rather than written by the plugin author.
_Also_: 自动生成功能项

**已禁用命令**:
An Alconna command currently unavailable for user invocation. It does not create an automatically detected function item.

**Alconna Help 接管**:
PicMenu Next handling an Alconna-requested current-command help response. It returns a PicMenu help view when possible and the original Alconna help otherwise.

**全局 Alconna Help 接管开关**:
The deployment setting that enables PicMenu Next to handle help requests for recognized Alconna commands.
_Also_: `PMN_ALCONNA_GLOBAL_EXT`

**当前命令帮助**:
The help response for the concrete Alconna command the user has already invoked.

**插件 Metadata**:
The plugin-authored metadata that describes the plugin and may include its PicMenu help data.
_Also_: 插件元数据, 手写菜单数据

**未声明 Metadata 的插件**:
A loaded plugin whose author has not supplied `PluginMetadata`. It remains eligible for a plugin menu item.

**发行包元数据**:
Version, maintainer, and summary information published by an installed Python distribution.

**展示信息补全**:
The fallback-source hierarchy used to supply a plugin menu item's display metadata when its PicMenu-specific metadata omits it.

**PicMenu 扩展配置**:
PicMenu Next-specific configuration embedded in plugin Metadata or external menu config.
_Also_: `pmn`

**Markdown 渲染开关**:
The PicMenu extension setting that makes help content render as Markdown.
_Also_: `markdown`

**PicMenu Markdown**:
The text format used to write help content when Markdown rendering is enabled.

**强制自动探测**:
The plugin Metadata setting that keeps Alconna auto-detection enabled even when function items are already declared.
_Also_: `alc_force_enable_detect`

**插件描述**:
The plugin-level summary shown in plugin help.
_Also_: `description`

**插件用法**:
The plugin-level usage help shown in plugin help.
_Also_: `usage`

**名称**:
The user-facing name of a plugin menu entry.
_Also_: `name`

**ID**:
The stable identifier used to match a plugin menu entry with plugin Metadata or external menu config.
_Also_: `plugin_id`

**已加载插件**:
A real NoneBot plugin already loaded by NoneBot. PicMenu Next consumes loaded plugins but does not discover or load plugins itself.

**外部菜单配置**:
User-maintained help data outside the plugin's own metadata.
_Avoid_: 插件 Metadata

**外部插件菜单**:
A plugin menu item created entirely from external menu config, without requiring a loaded plugin. It participates in menu sorting, querying, rendering, hidden-plugin semantics, and hidden function-item semantics like other plugin menu items.

**外部菜单兼容入口**:
A legacy entry point for loading external menu config during migration.

**插件资源路径**:
A relative resource reference resolved within the target plugin's resource root rather than at a web URL or process working directory.

**插件资源根目录**:
The module directory of the plugin named by a plugin resource path. It is the boundary of files that the reference may access.

**资源路径越界**:
An invalid plugin resource path that resolves outside the target plugin's resource root.

**PicMenu 富文本**:
A PicMenu-compatible input format that uses `<ft>` tags to describe the presentation of part of a help text.
_Avoid_: 推荐格式

**菜单数据 Mixin**:
An extension point that lets another plugin adjust PicMenu help data before menu views are rendered.
_Also_: 首页 Mixin

**详情数据 Mixin**:
An extension point that lets another plugin adjust one plugin's help data before detail views are rendered.
_Also_: 插件详情 Mixin, 功能详情 Mixin

**Mixin 优先级**:
The numeric value that determines the nesting order of Mixins of the same kind.

**库插件**:
A plugin whose primary role is to support other plugins rather than expose user-facing features.

**支持适配器**:
The bot adapters a plugin menu entry declares as supported.

**隐藏插件**:
A plugin omitted from the normal help homepage. Plugin visibility is independent from function-item visibility.
_Avoid_: 隐藏内容

**插件隐藏开关**:
The plugin-level setting that marks a plugin menu entry as a hidden plugin.
_Also_: `hidden`

**适配器隐藏插件**:
A hidden plugin whose current bot adapter is not supported by that plugin.

**隐藏功能项**:
A function item omitted from the normal plugin detail page. Function-item visibility is independent from plugin visibility.
_Also_: 隐藏三级菜单项
_Avoid_: 隐藏内容

**功能项隐藏开关**:
The function-item setting that marks a function item as hidden.
_Also_: `pmn_hidden`

**显示隐藏项**:
A menu command option that includes hidden plugins and hidden function items in normal help-menu rendering.
_Also_: 显示隐藏插件

**隐藏项权限策略**:
The rule that decides whether a user may explicitly display hidden plugins and hidden function items in normal help-menu rendering.

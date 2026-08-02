# PicMenu Next

PicMenu Next maintains the language for a NoneBot plugin help-menu context. These terms describe the user-facing help domain, not implementation details.

## Language

**帮助菜单聚合与渲染**:
The core responsibility of PicMenu Next: collecting help data and presenting it as help-menu views.

**帮助首页**:
The top-level help view that lists available plugins.
_Also_: 一级菜单

**插件详情页**:
The help view for one plugin, showing its plugin-level description and its child help entries.
_Also_: 二级菜单

**功能详情页**:
The help view for one function item.
_Also_: 三级菜单

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

**功能项**:
A help entry under a plugin that describes one user-facing feature, including how it is triggered and what it does.
_Also_: 三级菜单项

**Alconna 自动探测**:
The process of discovering PicMenu help data from registered Alconna commands.

**自动探测功能项**:
A function item discovered from an existing command declaration rather than written by the plugin author.
_Also_: 自动生成功能项

**Alconna Help 接管**:
Rendering Alconna command help through PicMenu Next instead of returning the original command help text.

**当前命令帮助**:
The help response for the concrete Alconna command the user has already invoked.

**插件 Metadata**:
The plugin-authored metadata that describes the plugin and may include its PicMenu help data.
_Also_: 插件元数据, 手写菜单数据

**外部菜单配置**:
User-maintained help data outside the plugin's own metadata.
_Avoid_: 插件 Metadata

**外部插件菜单**:
A plugin menu entry created entirely from external menu config, without requiring a loaded plugin.

**插件资源路径**:
A resource reference rooted at a plugin package rather than at a web URL or process working directory.

**PicMenu 富文本**:
A legacy PicMenu-compatible rich text input format accepted for migration and compatibility.
_Avoid_: 推荐格式

**菜单数据 Mixin**:
An extension point that lets another plugin adjust PicMenu help data before menu views are rendered.
_Also_: 首页 Mixin

**详情数据 Mixin**:
An extension point that lets another plugin adjust one plugin's help data before detail views are rendered.
_Also_: 插件详情 Mixin, 功能详情 Mixin

**库插件**:
A plugin whose primary role is to support other plugins rather than expose user-facing features. Library plugins are hidden by default unless PicMenu help data explicitly makes them visible.

**隐藏插件**:
A plugin omitted from the normal help homepage. Plugin visibility is independent from function-item visibility.
_Avoid_: 隐藏内容

**适配器隐藏插件**:
A hidden plugin whose current bot adapter is not supported by that plugin.

**隐藏功能项**:
A function item omitted from the normal plugin detail page. Function-item visibility is independent from plugin visibility.
_Also_: 隐藏三级菜单项
_Avoid_: 隐藏内容

**显示隐藏项**:
A menu command option that includes hidden plugins and hidden function items in normal help-menu rendering.
_Also_: 显示隐藏插件

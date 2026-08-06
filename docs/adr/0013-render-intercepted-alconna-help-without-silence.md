---
status: accepted
---

# Render Intercepted Alconna Help Without Silence

Normal help-menu queries respect hidden plugins and hidden function items: if a plugin is hidden, users cannot find it through the ordinary menu command, and explicit display of hidden items remains subject to hidden-item permission policy. Adapter support can hide a plugin as part of the menu data transformation path, and later Mixin changes take precedence over that derived hidden state. Alconna Help interception is different because the user has already invoked a concrete command, so PicMenu Next must return Help for that command regardless of plugin or function-item hidden state. It uses the same data path as ordinary plugin and function detail rendering; when the current command has no registered function item, it may create a temporary item for that render.

Alconna decides whether a `-h` or `--help` invocation requests output. Once PicMenu Next receives such a request for a recognized command, it must return a response. It first attempts a PicMenu help view with the same adapter and hidden-state filtering as ordinary menu discovery. Only a normal no-result, such as a missing plugin or function item (including an item hidden by that first attempt), triggers one retry with hidden-state filtering relaxed. That retry uses the `-H` snapshot, including adapter-hidden plugins, so any numeric menu-navigation guidance remains resolvable. If that retry still has no view, PicMenu Next returns Alconna's original help output.

All PicMenu interception steps are protected as one operation. Any ordinary exception, including command ownership resolution, context injection, Mixin execution, or template rendering, is logged with `logger.exception` together with the command path and plugin ID, then immediately returns Alconna's original help output without a hidden-state retry. A failed interception must never turn an Alconna help request into silence.

---
status: accepted
---

# Render Alconna Help Regardless of Hidden State

Normal help-menu queries respect hidden plugins and hidden function items: if a plugin is hidden, users cannot find it through the ordinary menu command, and explicit display of hidden items remains subject to hidden-item permission policy. Adapter support can hide a plugin as part of the menu data transformation path, and later Mixin changes take precedence over that derived hidden state. Alconna help interception is different because the user has already invoked a concrete command, so PicMenu Next must return help for that command regardless of plugin or function-item hidden state. The intercepted help should still use the same data path as ordinary plugin and function detail rendering, with hidden-state filtering and hidden-item permission checks relaxed for the current command; when the current command has no registered function item, PicMenu Next may create a temporary function item for that render.

Alconna decides whether a `-h` or `--help` invocation requests output. Once PicMenu Next receives such a request for a recognized command, it must return a response: it first attempts a PicMenu help view without hidden-state or adapter filtering, then returns Alconna's original help output if no view can be rendered. A failed interception must never turn an Alconna help request into silence.

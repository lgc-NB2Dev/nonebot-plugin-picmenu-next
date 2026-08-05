---
status: accepted
---

# Treat Menu Visibility as Discovery, Not Authorization

PicMenu Next omits hidden plugins and function items from ordinary help-menu discovery, but does not treat that state as an access-control boundary. By default, any user may explicitly include both kinds of hidden item with `-H` or `--show-hidden`; a deployment may restrict that option to superusers when it needs a limited view. The option relaxes only the `hidden` switches: it does not bypass adapter-support filtering. Plugin authors must not rely on `hidden` to keep information secret.

Library plugins are hidden from ordinary help-menu views unless their PicMenu help data explicitly sets the plugin hidden switch to visible. They follow the same `--show-hidden` rule as any other hidden plugin. This keeps the homepage focused on user-facing features while retaining an opt-in for a library plugin that intentionally exposes commands.

---
status: accepted
---

# Store Adapter Support as Menu Data

Supported adapters are plugin-level menu data, not transient metadata or PicMenu extension configuration. PicMenu Next stores them internally as `set[str] | None`, accepts an array in external JSON/YAML/TOML config, collects `PluginMetadata.supported_adapters`, and lets external config replace that field as a whole so loaded and external plugin menus share one visibility model.

Missing or `null` adapter data means all adapters are supported, while an explicit empty list supports none and hides the plugin from ordinary menu discovery. `-H` or `--show-hidden` includes that adapter-hidden plugin, but does not make it compatible with the current adapter. Unresolvable entries are ignored without failing the menu but do not establish support. Adapter hiding is derived from final menu data before Mixins run, so a Mixin may override it; it affects only ordinary menu visibility, not Help interception for a command the user has already invoked.

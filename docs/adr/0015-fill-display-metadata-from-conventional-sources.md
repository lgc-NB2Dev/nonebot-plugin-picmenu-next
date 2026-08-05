---
status: accepted
---

# Fill Display Metadata From Conventional Sources

PicMenu Next uses plugin-authored PicMenu metadata first for display information, then fills version from the module `__version__` and installed distribution version, and fills author from installed distribution author, maintainer, or email metadata. Help descriptions remain owned by `PluginMetadata` when it exists; the distribution summary is used only when the plugin has no Metadata at all. This keeps help-specific descriptions under plugin-author control while showing useful version and author information for plugins that omit redundant fields.

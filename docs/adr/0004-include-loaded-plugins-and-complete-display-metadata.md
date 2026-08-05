---
status: accepted
---

# Include Loaded Plugins and Complete Display Metadata

PicMenu Next creates a plugin menu item for every loaded plugin, including one without `PluginMetadata`. Metadata enriches and curates that item but is not an admission requirement; names, conventional display metadata, and Alconna detection provide useful fallbacks. Library-plugin hiding and explicit PicMenu visibility controls remain the ways to remove implementation-oriented plugins from ordinary discovery.

PicMenu-specific metadata takes precedence for display information. Version falls back to module `__version__` and then the installed distribution version; author falls back to the distribution author, maintainer, or email metadata. A `PluginMetadata` description remains authoritative when present, and the distribution summary is used only for a plugin without Metadata.

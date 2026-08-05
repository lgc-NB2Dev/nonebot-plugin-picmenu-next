---
status: accepted
---

# Use External Menu Filename as Plugin ID

External menu config uses the config file stem as the plugin ID. That ID decides whether the config overrides a loaded plugin menu or creates an external plugin menu, keeping identity in the filesystem name instead of duplicating it inside every file. When a config creates an external plugin menu and omits `name`, PicMenu Next derives the display name from the plugin ID/file stem. Within one configuration source, duplicate plugin IDs, including files that differ only by extension, are undefined behavior: filesystem enumeration decides which one is first, and PicMenu Next warns and ignores later files with the same ID. The localstore config directory is the primary external menu entry point, while the old PicMenu menu directory is kept as an external menu compatibility entry for migration; this source precedence remains defined. Optional top-level display fields other than `name` may be explicitly set to `null` to clear collected Metadata values; `name = null` is not accepted because every plugin menu item must have a name.

PicMenu Next recursively discovers JSON, YAML, and TOML files in each external-menu source. Subdirectories are only an organizational tool: they do not namespace plugin IDs, so every file stem in one source must remain unique across all supported formats and directory levels. YAML and TOML support depends on their parser availability; a file that cannot be parsed follows the source-failure isolation policy in ADR 0008.

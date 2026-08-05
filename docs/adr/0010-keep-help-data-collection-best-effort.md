---
status: accepted
---

# Keep Help Data Collection Best Effort

PicMenu Next treats help data collection as best-effort: one broken external menu config file or Mixin should not make the whole help menu unavailable. Failed sources are skipped after warning, and remaining collected menu data continues through rendering. Mixin changes are not transactional, so PicMenu Next does not roll back in-place mutations made before a Mixin fails.

An invalid PicMenu Metadata extension on a loaded plugin is handled differently: PicMenu Next warns and ignores the invalid extension while retaining the plugin's ordinary Metadata and conventional fallbacks. The plugin remains eligible for a menu item and Alconna detection; only the invalid PicMenu-specific data is discarded.

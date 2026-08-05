---
status: accepted
---

# Run Alconna Detection Before External Overrides

PicMenu Next resolves help data in this order: plugin Metadata, Alconna detection eligibility, external menu config, detected function-item generation, then Mixin. External menu config is a user override layer, so it should see and override automatically detected function items rather than suppressing detection by running before it; if an external config omits `funcs`, detected function items remain, and if it declares `funcs`, that list replaces them as a whole rather than merging item by item. The same explicit-list rule applies to plugin Metadata: `menu_data = []` means the plugin intentionally declares an empty function item list, while omitted or `None` `menu_data` leaves room for automatic detection. When Metadata enables `alc_force_enable_detect` alongside an explicit function-item list, generated function items are placed before the hand-written items. An explicit external `funcs` list also takes precedence over Metadata `alc_force_enable_detect`, so forced detection does not add detected function items back after the user has replaced the list. Detected function items are generated after external overrides and therefore follow the final presentation policy, such as Markdown rendering.

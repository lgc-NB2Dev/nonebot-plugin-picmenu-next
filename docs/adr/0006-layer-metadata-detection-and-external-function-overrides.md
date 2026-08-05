---
status: accepted
---

# Layer Metadata, Detection, and External Function Overrides

PicMenu Next resolves help data in this order: plugin Metadata, Alconna detection eligibility, external menu config, detected function-item generation, then Mixin. External config is a user override layer, so it sees and overrides automatically detected function items rather than suppressing detection by running first; if it omits `funcs`, detected items remain, and if it declares `funcs`, that complete list replaces them rather than merging item by item.

The same explicit-list rule applies to plugin Metadata: `menu_data = []` intentionally declares an empty function-item list, while omitted or `None` `menu_data` leaves room for automatic detection. When Metadata enables `alc_force_enable_detect` alongside an explicit function-item list, detected items are placed before hand-written items. An explicit external `funcs` list takes precedence over `alc_force_enable_detect`, so forced detection does not add items back after the user replaces the list; detected items are generated after external overrides and therefore follow final presentation policy such as Markdown rendering.

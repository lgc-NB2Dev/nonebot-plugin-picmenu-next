---
status: accepted
---

# Resolve Menu Queries by Snapshot Index, Name, and Pinyin

PicMenu Next orders plugin menu items by pinyin sort key and then by plugin ID, removing incidental plugin-load ordering when names share the same pinyin. A numeric query selects the 1-based position in that current sorted snapshot, not a stable identity; the position may change as menu items change.

A pure positive number is resolved as an index before name or pinyin matching. Zero and all-zero strings remain fuzzy queries; other queries combine the displayed name at 60% and pinyin at 40%, require a score of 60, and never replace displayed names with pinyin. This keeps direct selection predictable while retaining Chinese and romanized discovery for plugin and function items.

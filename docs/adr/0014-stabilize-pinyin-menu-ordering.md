---
status: accepted
---

# Stabilize Pinyin Menu Ordering

PicMenu Next orders plugin menu items by pinyin sort key and then by plugin ID. This removes incidental plugin-load ordering from menu positions when names share the same pinyin. A numeric menu query continues to select a 1-based position in the current menu snapshot; the index is a convenience for that snapshot, not a stable identity, and may change as menu items change.

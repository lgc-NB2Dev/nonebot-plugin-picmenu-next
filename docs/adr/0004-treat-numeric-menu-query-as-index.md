---
status: superseded by ADR 0011
---

# Treat Numeric Menu Query as Index

Menu queries interpret a pure positive number as a 1-based index before any name or pinyin matching. Zero and all-zero strings are not valid indexes and fall through to fuzzy matching. Non-numeric queries use fuzzy matching over both the original names and pinyin so users can find plugins and function items by readable names or romanized input, and scores below the cutoff are treated as no match. Pinyin is also used as a sorting/search aid, but it never replaces the displayed names.

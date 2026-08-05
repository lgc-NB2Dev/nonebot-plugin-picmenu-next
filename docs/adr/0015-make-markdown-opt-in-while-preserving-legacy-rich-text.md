---
status: accepted
---

# Make Markdown Opt-In While Preserving Legacy Rich Text

PicMenu Next leaves `pmn.markdown` disabled by default for plugin Metadata and external menu config. A plugin author or operator enables Markdown explicitly when its help content is written for that format, preserving existing plain text and PicMenu rich-text content without reinterpreting punctuation or tags after an upgrade.

Markdown capability is defined by the installed `markdown-it-py` dependency and the plugins applied to its Markdown instance; PicMenu Next keeps ownership of that parser configuration rather than maintaining a second syntax inventory. The legacy PicMenu rich-text format remains accepted for migrated content while Markdown is recommended, and malformed legacy text falls back to safe plain-text layout so it cannot make the help menu unavailable.

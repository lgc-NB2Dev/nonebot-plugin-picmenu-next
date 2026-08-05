---
status: accepted
---

# Make Markdown Rendering Opt-In

PicMenu Next leaves `pmn.markdown` disabled by default for plugin Metadata and external menu config. A plugin author or operator enables Markdown explicitly when its help content is written for that format. This preserves existing plain text and PicMenu rich-text content without reinterpreting punctuation or tags after an upgrade, while making Markdown adoption a conscious declaration.

---
status: accepted
---

# Delegate Markdown Capability to Parser Configuration

PicMenu Next defines its Markdown help-content capability through the installed `markdown-it-py` dependency and the plugins applied to its Markdown instance. The project does not maintain a second syntax inventory, so plugin authors and users have one authoritative source for supported Markdown behavior while PicMenu Next keeps ownership of the parser configuration it applies.

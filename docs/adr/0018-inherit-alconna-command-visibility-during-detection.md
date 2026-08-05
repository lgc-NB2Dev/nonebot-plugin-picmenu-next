---
status: accepted
---

# Inherit Alconna Command Visibility During Detection

PicMenu Next omits disabled Alconna commands from automatic detection and maps a detected command's `meta.hide` setting to the function item's hidden state. A PicMenu command override may explicitly replace that hidden state. This keeps ordinary help-menu discovery within the command author's public visibility boundary while preserving a deliberate PicMenu-specific escape hatch; it does not restrict help for a command the user has already invoked, as defined by ADR 0002.

---
status: accepted
---

# Resolve Function Templates With Fallback

Function detail rendering chooses a function item's template first, then the final plugin template when inheritance is enabled, then the configured/default function-detail template. This rule is the same for hand-written and Alconna-detected function items; external menu config can override the plugin template before inheritance is resolved. The inheritance switch controls only whether the plugin template is reused for function detail rendering, not plugin detail rendering itself.

When a selected template is missing, PicMenu Next falls back instead of failing the help render. A missing plugin-selected template falls back to the user-configured template for that view type, and a missing user-configured template falls back to built-in `default`; if that final built-in fallback is unavailable, rendering may fail because the installation or packaged resources are broken.

---
status: accepted
---

# Function Template Overrides Plugin Template

Function detail rendering chooses any function item's template first, then falls back to the final plugin template when inheritance is enabled, then falls back to the configured/default function-detail template. This rule is the same for hand-written and Alconna-detected function items. It lets a plugin set a common visual style while allowing individual function items to opt into a more specific template when needed; external menu config can override the plugin template before inheritance is resolved. The inheritance switch only controls whether the plugin template is reused for function detail rendering; it does not affect plugin detail rendering itself.

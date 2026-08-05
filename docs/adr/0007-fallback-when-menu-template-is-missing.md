---
status: accepted
---

# Fallback When Menu Template Is Missing

When a selected menu template is missing, PicMenu Next falls back instead of failing the help render. Plugin-selected templates fall back to the user-configured template for that view type, and a missing user-configured template falls back to the built-in `default` template so help menus remain available. If the final built-in fallback is unavailable, rendering may fail because the installation or packaged template resources are broken.

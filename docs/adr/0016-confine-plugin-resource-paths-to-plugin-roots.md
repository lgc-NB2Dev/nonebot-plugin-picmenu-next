---
status: accepted
---

# Confine Plugin Resource Paths to Plugin Roots

PicMenu Next treats `plugin:` resource references as relative paths confined to the resolved module directory of the target plugin. Absolute paths and paths that resolve outside that directory, including through `..` or symlinks, are invalid and must not be read or served by either Base64 or local-file rendering. Invalid references follow the existing unresolved-resource behavior: they remain unchanged and do not make the help menu unavailable. This preserves `plugin:` as a plugin-resource reference rather than a general local-file access mechanism.

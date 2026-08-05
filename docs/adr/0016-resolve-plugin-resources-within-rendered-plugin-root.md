---
status: accepted
---

# Resolve Plugin Resources Within the Rendered Plugin Root

In a plugin resource path, `plugin:self,...` refers to the plugin currently being rendered rather than the plugin or extension that authored the Markdown text. Cross-plugin resources name their target explicitly. Resolution applies only to supported Markdown image and link targets and HTML `src`, `href`, and `poster` attributes; an unresolved target remains unchanged instead of failing the menu render.

PicMenu Next resolves each `plugin:` reference relative to the target plugin's module directory. Absolute paths and paths outside that root, including `..` and symlink escapes, are invalid and are not read or served by Base64 or local-file rendering. Invalid references remain unchanged, preserving `plugin:` as a plugin-resource reference rather than a general local-file access mechanism.

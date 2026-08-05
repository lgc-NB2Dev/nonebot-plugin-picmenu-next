---
status: accepted
---

# Preserve Help Command Invocation Contract

PicMenu Next keeps `help` as the canonical help command with `帮助` and `菜单` as fixed Chinese aliases, and each invocation observes the runtime command-start configuration. This gives deployments a predictable, documented public entry point; making names configurable would make command conflicts easier to avoid but would fragment user instructions and compatibility expectations.

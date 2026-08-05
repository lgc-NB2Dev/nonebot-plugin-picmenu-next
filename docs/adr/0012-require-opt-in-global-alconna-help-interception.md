---
status: accepted
---

# Require Opt-In Global Alconna Help Interception

PicMenu Next leaves global Alconna Help interception disabled by default and enables it only when a deployment sets `PMN_ALCONNA_GLOBAL_EXT`. Interception changes the help experience of recognized commands owned by other plugins, so it must be an operator's deliberate choice rather than an installation side effect. Deployments that want a consistent image-help experience can opt in explicitly.

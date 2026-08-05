---
status: accepted
---

# Treat Hidden Items as Discoverability by Default

PicMenu Next treats hidden plugins and function items as omitted from ordinary help-menu discovery, not as an access-control boundary. By default, any user may explicitly include them with `-H` or `--show-hidden`; a deployment may configure that option for superusers only when it needs a restricted view. Plugin authors must not rely on `hidden` to keep information secret, while operators retain a deliberate permission control where needed.

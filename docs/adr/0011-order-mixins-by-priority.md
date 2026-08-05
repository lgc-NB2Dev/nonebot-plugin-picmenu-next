---
status: accepted
---

# Order Mixins by Priority

PicMenu Next composes Mixins of the same kind by ascending numeric priority: a lower-priority Mixin enters before and returns after a higher-priority Mixin. Equal priorities retain runtime registration order, but that order is not a stable cross-plugin contract. This gives extension authors an explicit way to control layering while requiring distinct priorities whenever their relative order matters.

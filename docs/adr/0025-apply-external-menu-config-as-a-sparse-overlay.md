---
status: accepted
---

# Apply External Menu Config as a Sparse Overlay

External menu config is a sparse user override: only fields explicitly supplied at the top level or inside `pmn` replace collected Metadata values, and `pmn = {}` is a no-op. Detection policy remains plugin-authored, so external `pmn` cannot set `alc_force_enable_detect`.

External `pmn` must be an object and external `funcs` must be a list; neither accepts `null`. An explicit `funcs` list contains complete function items and replaces the collected list rather than patching individual items; ADR 0001 defines the resulting detection precedence.

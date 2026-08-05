---
status: accepted
---

# Use File-Identified External Menu Config as a Sparse Overlay

External menu config uses the config file stem as the plugin ID, deciding whether it overrides a loaded plugin menu or creates an external plugin menu. An external item without `name` derives its display name from that stem; optional top-level display fields other than `name` may be `null` to clear collected Metadata values, but `name = null` is invalid. Duplicate IDs in one source, including across file extensions or subdirectories, are invalid configuration: PicMenu Next warns and keeps one file, but callers must not rely on which one because filesystem enumeration is not an ordering contract.

PicMenu Next recursively discovers JSON, YAML, and TOML files in each external-menu source. Subdirectories organize files but do not namespace IDs. The localstore directory is primary: when both sources supply the same valid ID, its entry wins and the legacy PicMenu menu directory cannot replace it. The two source scans are independently best-effort, so an unavailable primary directory or an unparseable primary file does not prevent usable legacy entries from loading, as specified by ADR 0010. YAML and TOML support depends on their parser availability.

External menu config is a sparse user override: only fields explicitly supplied at the top level or inside `pmn` replace collected Metadata values, and `pmn = {}` is a no-op. Detection policy remains plugin-authored, so external `pmn` cannot set `alc_force_enable_detect`; external `pmn` must be an object and `funcs` a list, neither may be `null`, and an explicit `funcs` list contains complete function items rather than patches.

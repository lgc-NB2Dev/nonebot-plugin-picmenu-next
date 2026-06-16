# AGENTS.md

First: This project expects the working root to be `lgc-NB2Dev/workspace` because some required workspace-level files is not stored in this plugin project. If you are not working from that root (You can use `git remote -v` to check), stop and notify the user.

## Structure

To be added

## Rules

Currently empty

## Gotchas

- When preserving or changing Pydantic fields-set state, do not mutate the set returned by `model_fields_set()` directly with `.add()` or `.update()`. Prefer assigning through normal model fields with `setattr()` or `model.field = value` so Pydantic maintains its own field state across v1/v2 compatibility.
- Pydantic v1 supports `PrivateAttr`, but its `BaseModel.__setattr__` does not dispatch normal property setters. For internal private attributes that must work on both v1 and v2, write the private attribute directly (for example `item._alc_cmd_id = value`) and expose only a read property if needed; do not rely on `item.alc_cmd_id = value`.

# AGENTS.md

First: This project expects the working root to be github repo `lgc-NB2Dev/workspace` because some recommended workspace-level files is not stored in this plugin project. If you are not working from that root, stop and notify the user.

## Commands

NOTE: The following command are expected to be run under the plugin repo root rather than the workspace root.

```bash
uv run scripts/gen_defs.py
uv run pytest
```

## Structure

- `data_source/`: Plugin info models (`PMNPluginInfo`, `PMDataItem`), data collection (Alconna / plugin metadata), pinyin matching
- `templates/`: Template rendering pipeline
  - `default/`: Built-in default template ("default") — Jinja2 templates, CSS, JS, image rendering entry point
  - `jj_utils.py`: Jinja2 context function factory (`build_base_render_kwargs`), global Jinja2 filters
  - `pw_utils.py`: Playwright route utilities (local-file route, `local_file_route_prp_transformer`)
  - `hr_utils.py`: htmlrender integration (template render instance, markdown style directory)
- `markdown.py`: `plugin:` resource path syntax processor — `PluginResPathProcessor`/`PluginResPathTransformer` type aliases, `build_default_prp_processor`, `resource_resolve_plugin`
- `__main__.py`: Command handler entry point (matchers, help menu logic)
- `config.py`: Plugin global config
- `ft_parser.py`: PicMenu custom Rich Text format parser
- `utils.py`: General utilities

## Rules

- Run `scripts/gen_defs.py` and `yarn prettier -cw defs/*` after changing `ExternalPluginInfo` and related models.

## Gotchas

- When preserving or changing Pydantic fields-set state, do not mutate the set returned by `model_fields_set()` directly with `.add()` or `.update()`. Prefer assigning through normal model fields with `setattr()` or `model.field = value` so Pydantic maintains its own field state across v1/v2 compatibility.
- Pydantic v1 supports `PrivateAttr`, but its `BaseModel.__setattr__` does not dispatch normal property setters. For internal private attributes that must work on both v1 and v2, write the private attribute directly (for example `item._alc_cmd_id = value`) and expose only a read property if needed; do not rely on `item.alc_cmd_id = value`.

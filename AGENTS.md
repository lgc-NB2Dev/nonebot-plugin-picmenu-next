# AGENTS.md

First: This project expects the working root to be github repo `lgc-NB2Dev/workspace` because some recommended workspace-level files is not stored in this plugin project. If you are not working from that root, stop and notify the user.

## Commands

NOTE: The following command are expected to be run under the plugin repo root rather than the workspace root.

```bash
poe gen-defs        # uv run scripts/gen_defs.py
poe test [...]      # pytest
poe coverage [...]  # pytest (with branch coverage and terminal report)
```

## Structure

```text
nonebot_plugin_picmenu_next/  Plugin package, help data collection and menu rendering
  __init__.py                 Plugin metadata, driver startup, refresh and template preload
  __main__.py                 Command handler: matchers, help interception, menu queries
  config.py                   Plugin global config model
  ft_parser.py                PicMenu legacy ft rich-text format parser
  markdown.py                 plugin resource path syntax processor
  utils.py                    Package name regex and general helpers
  data_source/                Help data models, collection and matching
    __init__.py               In-memory info cache, refresh_infos and get_infos
    models.py                 PMDataItem, PMNPluginInfo and ExternalPluginInfo schemas
    collect.py                Collects plugin metadata, menus and user custom infos
    alconna.py                Alconna help formatting and menu data projection
    pinyin.py                 Pinyin chunk matching for menu queries
    mixin.py                  Mixin collectors, priority chain, main/detail resolution
  templates/                  Template rendering pipeline
    __init__.py               Builtin template discovery, loading and registration
    jj_utils.py               Jinja2 render kwargs builder and global filters
    pw_utils.py               Playwright local-file route helpers
    hr_utils.py               htmlrender integration and KaTeX resource lookup
    default/                  Builtin default template
      __init__.py             Registers default index, detail and function renderers
      res/
        base.html.jinja       Base layout page
        index.html.jinja      Plugin list page
        detail.html.jinja     Plugin detail page
        css/                  4 stylesheets: base, dark, index, detail
        js/                   Empty, reserved for template scripts
        third-party/          2 code highlight themes: code-colorful, code-github-dark
  res/
    gan_shen_me.jpg           Tip image shown when hidden menu access is denied
tests_nbp_picmenu_next/       Pytest suite mirroring the plugin package; shared fixtures in conftest.py
docs/
  development.md              Development guide
  adr/                        16 numbered ADRs 0001-0016 recording design decisions
scripts/
  gen_defs.py                 Generates defs/ExternalPluginInfo.json from models
defs/
  ExternalPluginInfo.json     Generated schema for external plugin info
.github/workflows/            CI test and PyPI publish workflows
CONTEXT.md                    Domain language reference for the help-menu context
```

## Rules

- Keep test coverage as high as possible to avoid dead code. Code included in the current runtime's coverage scope should be covered unless it is version-specific, dependency-gated, or an intentional error path that is impractical to trigger safely.

- Run `scripts/gen_defs.py` and `yarn prettier -cw defs/*` after changing `ExternalPluginInfo` and related models.

## Gotchas

- When preserving or changing Pydantic fields-set state, do not mutate the set returned by `model_fields_set()` directly with `.add()` or `.update()`. Prefer assigning through normal model fields with `setattr()` or `model.field = value` so Pydantic maintains its own field state across v1/v2 compatibility.

- Pydantic v1 supports `PrivateAttr`, but its `BaseModel.__setattr__` does not dispatch normal property setters. For internal private attributes that must work on both v1 and v2, write the private attribute directly (for example `item._alc_cmd_id = value`) and expose only a read property if needed; do not rely on `item.alc_cmd_id = value`.

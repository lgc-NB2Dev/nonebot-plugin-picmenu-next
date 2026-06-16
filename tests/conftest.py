from pathlib import Path
from typing import Any

import pytest

TEST_NB2_DIR = Path(__file__).parents[3] / "private" / "test-nb2"


def pytest_configure(config: pytest.Config) -> None:
    from nonebug import NONEBOT_INIT_KWARGS

    init_kwargs = dict(config.stash.get(NONEBOT_INIT_KWARGS, {}))
    init_kwargs.update(
        {
            "driver": "~fastapi+~websockets+~httpx",
            "localstore_cache_dir": TEST_NB2_DIR / "cache",
            "localstore_config_dir": TEST_NB2_DIR / "config",
            "localstore_data_dir": TEST_NB2_DIR / "data",
            "log_level": "DEBUG",
            "render_backend": "playwright",
        }
    )
    config.stash[NONEBOT_INIT_KWARGS] = init_kwargs


@pytest.fixture
def picmenu_plugin(app: Any):  # noqa: ARG001
    import importlib

    import nonebot

    if plugin := nonebot.get_plugin("nonebot_plugin_picmenu_next"):
        return plugin
    try:
        return nonebot.load_plugin("nonebot_plugin_picmenu_next")
    except RuntimeError as e:
        if "Plugin already exists" not in str(e):
            raise
    return importlib.import_module("nonebot_plugin_picmenu_next")

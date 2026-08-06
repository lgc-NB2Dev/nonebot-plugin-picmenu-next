"""Tests for Markdown rendering and plugin-resource resolution."""

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import pytest
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo
    from nonebot_plugin_picmenu_next.markdown import (
        PluginResPathProcessor,
        PluginResPathProcessPluginEnv,
    )


def _make_info():
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    return PMNPluginInfo(name="TestPlugin", plugin_id="test_plugin")


def _make_prp_processor() -> "PluginResPathProcessor":
    def _prp(info: "PMNPluginInfo", path: str) -> str:
        return path.replace("plugin:self,", "/resolved/").replace(
            "plugin:other,",
            "/resolved-other/",
        )

    return _prp


def _env(
    info: "PMNPluginInfo",
    prp: "PluginResPathProcessor",
) -> "PluginResPathProcessPluginEnv":
    return cast("PluginResPathProcessPluginEnv", {"info": info, "prp_processor": prp})


def _render(md_text: str, *args: Any, **kwargs: Any) -> str:
    from nonebot_plugin_picmenu_next.markdown import md

    return md.render(md_text, *args, **kwargs)


def _make_default_prp_processor(
    module_root: Path,
    monkeypatch: "pytest.MonkeyPatch",
) -> "PluginResPathProcessor":
    from nonebot_plugin_picmenu_next import markdown

    plugin = SimpleNamespace(module=SimpleNamespace(__path__=[str(module_root)]))
    monkeypatch.setattr(markdown, "get_plugin", lambda _plugin_id: plugin)
    return markdown.build_default_prp_processor(markdown.b64_prp_transformer)


# === image token ===


def test_image_src_with_plugin_self(picmenu_plugin: object):
    result = _render(
        "![alt](plugin:self,img/foo.png)",
        env=_env(_make_info(), _make_prp_processor()),
    )
    assert 'src="/resolved/img/foo.png"' in result


def test_image_src_with_plugin_other(picmenu_plugin: object):
    result = _render(
        "![alt](plugin:other,img/bar.png)",
        env=_env(_make_info(), _make_prp_processor()),
    )
    assert 'src="/resolved-other/img/bar.png"' in result


def test_image_src_without_plugin_prefix_unchanged(picmenu_plugin: object):
    result = _render(
        "![alt](https://example.com/img.png)",
        env=_env(_make_info(), _make_prp_processor()),
    )
    assert 'src="https://example.com/img.png"' in result


def test_image_src_without_env_unchanged(picmenu_plugin: object):
    result = _render("![alt](plugin:self,img/foo.png)")
    assert 'src="plugin:self,img/foo.png"' in result


def test_plugin_resource_outside_module_root_is_unchanged(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """A menu cannot render a plugin resource outside its module root."""
    module_root = tmp_path / "plugin"
    module_root.mkdir()
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    processor = _make_default_prp_processor(module_root, monkeypatch)

    result = _render(
        "![alt](plugin:self,../secret.txt)",
        env=_env(_make_info(), processor),
    )

    assert 'src="plugin:self,../secret.txt"' in result


def test_local_file_renderer_rejects_plugin_resource_outside_module_root(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """The default local-file renderer cannot serve files outside a plugin root."""
    from nonebot_plugin_picmenu_next import markdown
    from nonebot_plugin_picmenu_next.templates.default import prp_processor

    module_root = tmp_path / "plugin"
    module_root.mkdir()
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    plugin = SimpleNamespace(module=SimpleNamespace(__path__=[str(module_root)]))
    monkeypatch.setattr(markdown, "get_plugin", lambda _plugin_id: plugin)

    result = _render(
        "![alt](plugin:self,../secret.txt)",
        env=_env(_make_info(), prp_processor),
    )

    assert 'src="plugin:self,../secret.txt"' in result


def test_plugin_resource_within_module_root_is_rendered(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """A menu can render a resource inside its plugin module root."""
    module_root = tmp_path / "plugin"
    module_root.mkdir()
    (module_root / "logo.txt").write_text("logo", encoding="utf-8")
    processor = _make_default_prp_processor(module_root, monkeypatch)

    result = _render(
        "![alt](plugin:self,logo.txt)",
        env=_env(_make_info(), processor),
    )

    assert 'src="data:text/plain;base64,bG9nbw=="' in result


def test_missing_plugin_resource_is_unchanged(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """A missing plugin resource leaves its menu reference unchanged."""
    module_root = tmp_path / "plugin"
    module_root.mkdir()
    processor = _make_default_prp_processor(module_root, monkeypatch)

    result = _render(
        "![alt](plugin:self,missing.txt)",
        env=_env(_make_info(), processor),
    )

    assert 'src="plugin:self,missing.txt"' in result


def test_plugin_resource_absolute_path_is_unchanged(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """A menu cannot render an absolute plugin resource path."""
    module_root = tmp_path / "plugin"
    module_root.mkdir()
    secret_path = module_root / "secret.txt"
    secret_path.write_text("secret", encoding="utf-8")
    processor = _make_default_prp_processor(module_root, monkeypatch)
    resource_path = secret_path.as_posix()

    result = _render(
        f"![alt](plugin:self,{resource_path})",
        env=_env(_make_info(), processor),
    )

    assert f'src="plugin:self,{resource_path}"' in result


def test_plugin_resource_rooted_path_is_unchanged(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """A menu cannot render a rooted path without a drive prefix."""
    module_root = Path(tmp_path.anchor)
    secret_path = tmp_path / "secret.txt"
    secret_path.write_text("secret", encoding="utf-8")
    processor = _make_default_prp_processor(module_root, monkeypatch)
    resource_path = secret_path.as_posix().removeprefix(secret_path.drive)

    result = _render(
        f"![alt](plugin:self,{resource_path})",
        env=_env(_make_info(), processor),
    )

    assert f'src="plugin:self,{resource_path}"' in result


def test_plugin_resource_symlink_outside_module_root_is_unchanged(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """A menu cannot escape its module root through a symbolic link."""
    import pytest

    module_root = tmp_path / "plugin"
    module_root.mkdir()
    secret_path = tmp_path / "secret.txt"
    secret_path.write_text("secret", encoding="utf-8")
    link_path = module_root / "secret-link.txt"
    try:
        link_path.symlink_to(secret_path)
    except OSError:
        pytest.skip("Creating symbolic links is unavailable in this environment")
    processor = _make_default_prp_processor(module_root, monkeypatch)

    result = _render(
        "![alt](plugin:self,secret-link.txt)",
        env=_env(_make_info(), processor),
    )

    assert 'src="plugin:self,secret-link.txt"' in result

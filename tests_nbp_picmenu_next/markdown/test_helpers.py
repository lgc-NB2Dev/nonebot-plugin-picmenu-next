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


def test_markdown_helpers_escape_and_render_math(
    picmenu_plugin: object,
) -> None:
    """Code and math helpers produce escaped HTML with the selected math mode."""
    from nonebot_plugin_picmenu_next import markdown

    assert markdown.highlight_code("<tag>", "", {}) == "&lt;tag&gt;"
    assert markdown.render_math_script("x < y", {}) == (
        '<script type="math/tex">x &lt; y</script>'
    )
    assert markdown.render_math_script("x", {"display_mode": True}) == (
        '<script type="math/tex; mode=display">x</script>'
    )
    assert "<span" in markdown.highlight_code("print(1)", "python", {})


def test_default_resource_processor_leaves_invalid_references_unchanged(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """A malformed or unavailable plugin reference remains ordinary Markdown text."""
    from nonebot_plugin_picmenu_next import markdown
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    monkeypatch.setattr(markdown, "get_plugin", lambda _plugin_id: None)
    processor = markdown.build_default_prp_processor(lambda *_args: "unreachable")
    info = PMNPluginInfo(name="plugin", plugin_id="plugin")

    assert (
        processor(info, "https://example.com/image.png")
        == "https://example.com/image.png"
    )
    assert processor(info, "plugin:self") == "plugin:self"
    assert processor(info, "plugin:missing,file.txt") == "plugin:missing,file.txt"


def test_b64_resource_transformer_reads_a_resolved_relative_path(
    picmenu_plugin: object,
    tmp_path: Path,
) -> None:
    """The default resource transformer encodes an in-root file as a data URL."""
    from nonebot_plugin_picmenu_next import markdown

    (tmp_path / "asset.txt").write_text("asset", encoding="utf-8")

    result = markdown.b64_prp_transformer(
        "asset.txt",
        tmp_path,
        _make_info(),
        cast("Any", SimpleNamespace()),
    )

    assert result == "data:text/plain;base64,YXNzZXQ="


def test_plugin_self_resource_uses_the_rendered_plugin_root(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """ADR-0016 resolves plugin:self from the rendered subject, not content author."""
    from nonebot_plugin_picmenu_next import markdown
    from nonebot_plugin_picmenu_next.data_source.models import PMNPluginInfo

    rendered_root = tmp_path / "rendered"
    authored_root = tmp_path / "authored"
    rendered_root.mkdir()
    authored_root.mkdir()
    (rendered_root / "asset.txt").write_text("rendered", encoding="utf-8")
    (authored_root / "asset.txt").write_text("authored", encoding="utf-8")
    plugins = {
        "rendered_plugin": SimpleNamespace(
            module=SimpleNamespace(__path__=[rendered_root])
        ),
        "authored_plugin": SimpleNamespace(
            module=SimpleNamespace(__path__=[authored_root])
        ),
    }
    monkeypatch.setattr(markdown, "get_plugin", plugins.get)
    processor = markdown.build_default_prp_processor(
        lambda _path, module_path, _info, _plugin: module_path.name
    )

    result = processor(
        PMNPluginInfo(name="Rendered", plugin_id="rendered_plugin"),
        "plugin:self,asset.txt",
    )

    assert result == "rendered"


def test_explicit_cross_plugin_resource_uses_named_plugin_root(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
    tmp_path: Path,
) -> None:
    """ADR-0016 resolves an explicit plugin resource from that plugin's root."""
    from nonebot_plugin_picmenu_next import markdown

    rendered_root = tmp_path / "rendered"
    target_root = tmp_path / "target"
    rendered_root.mkdir()
    target_root.mkdir()
    (target_root / "asset.txt").write_text("target", encoding="utf-8")
    plugins = {
        "rendered": SimpleNamespace(module=SimpleNamespace(__path__=[rendered_root])),
        "target": SimpleNamespace(module=SimpleNamespace(__path__=[target_root])),
    }
    monkeypatch.setattr(markdown, "get_plugin", plugins.get)
    processor = markdown.build_default_prp_processor(
        lambda _path, module_path, _info, _plugin: module_path.name
    )

    result = processor(_make_info(), "plugin:target,asset.txt")

    assert result == "target"

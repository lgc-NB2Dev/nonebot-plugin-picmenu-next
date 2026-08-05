"""Tests for templates.jj_utils."""


def test_jinja_render_helpers_support_markdown_and_legacy_layout(
    picmenu_plugin: object,
) -> None:
    """Template context renders Markdown and retains safe fallback text layout."""
    from nonebot_plugin_picmenu_next.templates.jj_utils import build_base_render_kwargs

    kwargs = build_base_render_kwargs()

    assert "<h1>Title</h1>" in str(kwargs["markdown"]("# Title"))
    assert "<strong>bold</strong>" in str(kwargs["layout"]("**bold**", is_md=True))
    assert "plain text" in str(kwargs["layout"]("plain text"))


def test_legacy_rich_text_renders_and_malformed_content_falls_back_safely(
    picmenu_plugin: object,
) -> None:
    """ADR-0015 keeps valid legacy text and safely preserves malformed content."""
    from cookit.jinja.filters import safe_layout
    from nonebot_plugin_picmenu_next.templates.jj_utils import build_base_render_kwargs

    layout = build_base_render_kwargs()["layout"]
    valid = str(layout("<ft color=red>legacy</ft>"))
    malformed = "<ft invalid=value>legacy</ft>"

    assert "color: red" in valid
    assert "legacy" in valid
    assert str(layout(malformed)) == str(safe_layout(malformed))

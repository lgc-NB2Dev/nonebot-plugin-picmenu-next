"""Tests for ft_parser."""

import pytest


def test_text_chunk_formats_styles_and_escapes_html(
    picmenu_plugin: object,
) -> None:
    """A parsed chunk serializes supported styles while escaping its text content."""
    from nonebot_plugin_picmenu_next.ft_parser import TextChunk

    chunk = TextChunk(
        "<content>",
        fonts="A'B\\C",
        size=20,
        color=(1, 2, 3),
        stroke_width=2,
        stroke_fill="blue",
    )

    assert chunk.style_dict == {
        "font-family": "'A\\'B\\\\C'",
        "font-size": "20px",
        "color": "#010203",
        "-webkit-text-stroke-width": "2px",
        "-webkit-text-stroke-color": "blue",
        "paint-order": "stroke fill",
    }
    assert str(chunk).startswith('<span style="')
    assert "&lt;content&gt;" in str(chunk)


def test_parse_chunk_resolves_quoted_and_tuple_attributes(
    picmenu_plugin: object,
) -> None:
    """The legacy parser accepts quoted values and RGB or RGBA color tuples."""
    from nonebot_plugin_picmenu_next.ft_parser import parse_chunk

    chunk = parse_chunk(
        ' fonts="Noto Sans" size=18 color="(1,2,3)" stroke_width=1 '
        "stroke_fill='(4,5,6,7)' ",
        "content",
    )

    assert chunk.fonts == "Noto Sans"
    assert chunk.size == 18
    assert chunk.color == (1, 2, 3)
    assert chunk.stroke_width == 1
    assert chunk.stroke_fill == (4, 5, 6, 7)


@pytest.mark.parametrize(
    ("attrs", "message"),
    [
        ("=20", "Expected key"),
        ("size==20", "invalid literal"),
        ("unknown=1", "Invalid attribute"),
        ("size", "Unterminated key"),
        ("color=(300,0,0)", "Invalid color value"),
    ],
)
def test_parse_chunk_rejects_invalid_legacy_attributes(
    picmenu_plugin: object,
    attrs: str,
    message: str,
) -> None:
    """Malformed rich-text attributes produce a parse error rather than unsafe CSS."""
    from nonebot_plugin_picmenu_next.ft_parser import parse_chunk

    with pytest.raises(ValueError, match=message):
        parse_chunk(attrs, "content")


def test_parse_ft_preserves_plain_and_styled_segments(
    picmenu_plugin: object,
) -> None:
    """Legacy tags split the source into plain and styled chunks in source order."""
    from nonebot_plugin_picmenu_next.ft_parser import parse_ft, transform_ft

    chunks = parse_ft("before<ft color=red>middle</ft>after")

    assert [chunk.text for chunk in chunks] == ["before", "middle", "after"]
    assert chunks[1].color == "red"
    assert transform_ft("<ft size=12>text</ft>") == (
        '<span style="font-size: 12px">text</span>'
    )


def test_parse_ft_keeps_tagless_text_as_a_plain_chunk(
    picmenu_plugin: object,
) -> None:
    """Text without a complete legacy tag stays available as safe plain content."""
    from nonebot_plugin_picmenu_next.ft_parser import parse_ft

    assert [chunk.text for chunk in parse_ft("<ft incomplete")] == ["<ft incomplete"]


def test_parse_chunk_handles_spaces_escapes_and_parser_error_boundaries(
    picmenu_plugin: object,
) -> None:
    """Legacy attributes accept spaced and escaped values while rejecting malformed tails."""
    from nonebot_plugin_picmenu_next.ft_parser import parse_chunk

    chunk = parse_chunk(' size = 2 fonts="A\\"B" ', "content")

    assert chunk.size == 2
    assert chunk.fonts == 'A"B'
    with pytest.raises(ValueError, match="Invalid char"):
        parse_chunk("bad key=1", "content")
    with pytest.raises(ValueError, match="Unexpected char"):
        parse_chunk("size=2=3", "content")
    with pytest.raises(ValueError, match="Unterminated quote"):
        parse_chunk("fonts='unterminated", "content")

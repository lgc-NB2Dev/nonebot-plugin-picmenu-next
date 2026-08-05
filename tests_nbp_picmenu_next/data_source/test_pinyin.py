"""Tests for normalized pinyin menu-sort data."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


def test_pinyin_chunks_keep_tone_and_non_chinese_text(
    picmenu_plugin: object,
) -> None:
    """A pinyin chunk retains its tone while a non-Chinese chunk stays literal."""
    from nonebot_plugin_picmenu_next.data_source import pinyin as pinyin_module

    chinese = pinyin_module.PinyinChunk.from_pinyin_res("bang1")
    other = pinyin_module.PinyinChunk.from_pinyin_res(
        pinyin_module._NotCHNStr("Plugin")  # noqa: SLF001
    )

    assert chinese.is_pinyin is True
    assert str(chinese) == "bang1"
    assert chinese.casefold_str == "bang"
    assert other.is_pinyin is False
    assert str(other) == "Plugin"


def test_pinyin_chunk_casefold_calculation_lowercases_its_text(
    picmenu_plugin: object,
) -> None:
    """The underlying casefold calculation normalizes a pinyin syllable."""
    from nonebot_plugin_picmenu_next.data_source import pinyin as pinyin_module

    chunk = pinyin_module.PinyinChunk.from_pinyin_res("Bang1")

    assert pinyin_module.PinyinChunk.casefold_str.func(chunk) == "bang"


def test_pinyin_sequence_uses_segmenter_and_pinyin_results(
    picmenu_plugin: object,
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    """Menu sort data combines segmented Chinese output with literal segments."""
    from nonebot_plugin_picmenu_next.data_source import pinyin as pinyin_module

    monkeypatch.setattr(pinyin_module, "_lcut", lambda _text: ["帮助", "Plugin"])
    monkeypatch.setattr(
        pinyin_module,
        "pinyin",
        lambda *_args, **_kwargs: [["bang1"], [pinyin_module._NotCHNStr("Plugin")]],  # noqa: SLF001
    )

    result = pinyin_module.PinyinChunkSequence.from_raw("ignored")

    assert str(result) == "bang1 Plugin"
    assert result.casefold_str == "bang1 plugin"

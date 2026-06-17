from collections.abc import Callable
from contextlib import suppress
from functools import cached_property
from typing import NamedTuple
from typing_extensions import Self

from pypinyin import Style, pinyin


def _get_lcut() -> Callable[[str], list[str]]:
    """自动选择分词器: spacy_pkuseg > rjieba > jieba_fast > jieba"""
    with suppress(ImportError):
        import spacy_pkuseg as pkuseg  # pyright: ignore[reportMissingImports]

        seg = pkuseg.pkuseg(model_name="web")
        return lambda text: seg.cut(text)  # noqa: PLW0108

    with suppress(ImportError):
        import rjieba  # pyright: ignore[reportMissingImports]

        seg = rjieba.Jieba()
        return lambda text: list(seg.cut(text, hmm=True))

    with suppress(ImportError):
        from jieba_fast import lcut  # pyright: ignore[reportMissingImports]

        return lcut

    from jieba import lcut

    return lcut


_lcut = _get_lcut()


class _NotCHNStr(str):
    __slots__ = ()


class PinyinChunk(NamedTuple):
    is_pinyin: bool
    text: str
    tone: int = 0

    @classmethod
    def from_pinyin_res(cls, text: str) -> Self:
        is_pinyin = not isinstance(text, _NotCHNStr)
        tone = 0
        if is_pinyin:
            tone = int(text[-1])
            text = text[:-1]
        return cls(is_pinyin=is_pinyin, text=text, tone=tone)

    @cached_property
    def casefold_str(self) -> str:
        return self.text.casefold()

    def __str__(self):
        return f"{self.text}{self.tone}" if self.is_pinyin else self.text


class PinyinChunkSequence(list[PinyinChunk]):
    @classmethod
    def from_raw(cls, text: str) -> Self:
        transformed = pinyin(
            [x.strip() for x in _lcut(text)],
            style=Style.TONE3,
            errors=_NotCHNStr,
            neutral_tone_with_five=True,
        )
        return cls(PinyinChunk.from_pinyin_res(x[0]) for x in transformed)

    @cached_property
    def casefold_str(self) -> str:
        return str(self).casefold()

    def __str__(self):
        return " ".join(str(x) for x in self)

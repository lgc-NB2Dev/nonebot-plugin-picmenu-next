from functools import cached_property
from typing import NamedTuple
from typing_extensions import Self

import jieba
from pypinyin import Style, pinyin


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
            [x.strip() for x in jieba.lcut(text)],
            style=Style.TONE3,
            errors=lambda x: _NotCHNStr(x),
            neutral_tone_with_five=True,
        )
        return cls(PinyinChunk.from_pinyin_res(x[0]) for x in transformed)

    @cached_property
    def casefold_str(self) -> str:
        return str(self).casefold()

    def __str__(self):
        return " ".join(str(x) for x in self)

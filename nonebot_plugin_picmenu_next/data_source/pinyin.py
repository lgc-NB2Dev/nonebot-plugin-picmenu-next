from collections.abc import Iterable, Iterator, Sequence
from functools import cached_property
from typing import NamedTuple, Optional, Union, overload
from typing_extensions import Self, override

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


class PinyinChunkSequence(Sequence[PinyinChunk]):
    def __init__(self, iterable: Optional[Iterable[PinyinChunk]] = None):
        self.chunks: tuple[PinyinChunk, ...] = tuple(iterable) if iterable else ()

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

    def __lt__(self, other: "PinyinChunkSequence"):
        return self.chunks.__lt__(other.chunks)

    def __gt__(self, other: "PinyinChunkSequence"):
        return self.chunks.__gt__(other.chunks)

    def __eq__(self, other: object):
        return (
            self.chunks.__eq__(other.chunks)
            if isinstance(other, PinyinChunkSequence)
            else NotImplemented
        )

    @override
    def __iter__(self) -> Iterator[PinyinChunk]:
        return self.chunks.__iter__()

    @override
    def __len__(self) -> int:
        return self.chunks.__len__()

    @overload
    def __getitem__(self, index: int) -> PinyinChunk: ...
    @overload
    def __getitem__(self, index: slice) -> Self: ...
    @override
    def __getitem__(self, index: Union[int, slice]):
        if isinstance(index, slice):
            return type(self)(self.chunks[index])
        return self.chunks[index]

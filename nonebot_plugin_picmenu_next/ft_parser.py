r"""
兼容 PicMenu 的 <ft> 格式富文本解析器

在普通文本中穿插 <ft> 标签对，且标签对不可嵌套，
起始标签内各参数以空格分隔，键值之间以等号分隔，值上的引号可以省略，
格式示范如下：

```
这是一段<ft size=20 color=red>富文本</ft>喵喵喵
```

可用参数及其允许的值：

- fonts: str - 该块文本使用的字体名称
- size: int - 该块文本的字号
- color: COLOR_TUPLE_RE | str - 该块文本的颜色，可为 RGB 或 RGBA 格式 tuple 语法，或为 Web 颜色名称
- stroke_width: int - 该块文本的描边宽度
- stroke_fill: COLOR_TUPLE_RE | str - 该块文本的描边颜色，格式同 color
"""

import re
from dataclasses import dataclass
from enum import Enum, auto
from html import escape
from typing import Any, Optional, Union
from typing_extensions import TypeAlias

ColorType: TypeAlias = Union[str, tuple[int, int, int], tuple[int, int, int, int]]

COLOR_TUPLE_RE = re.compile(r"\(\s*(\d+?,\s*){2,3}(\d+?,?\s*)\)")


def format_color_css(color: ColorType) -> str:
    if isinstance(color, str):
        return color
    return f"#{''.join(f'{c:02x}' for c in color)}"


@dataclass
class TextChunk:
    text: str
    fonts: Optional[str] = None
    size: Optional[int] = None
    color: Optional[ColorType] = None
    stroke_width: Optional[int] = None
    stroke_fill: Optional[ColorType] = None

    @property
    def style_dict(self):
        style: dict[str, str] = {}
        if self.fonts:
            fonts = self.fonts.replace("\\", "\\\\").replace("'", "\\'")
            style["font-family"] = f"'{fonts}'"
        if self.size:
            style["font-size"] = f"{self.size}px"
        if self.color:
            style["color"] = format_color_css(self.color)
        if self.stroke_width and self.stroke_fill:
            style["-webkit-text-stroke-width"] = f"{self.stroke_width}px"
            style["-webkit-text-stroke-color"] = format_color_css(self.stroke_fill)
            style["paint-order"] = "stroke fill"
        return style

    @property
    def style(self) -> str:
        return "; ".join(f"{k}: {v}" for k, v in self.style_dict.items())

    def __str__(self) -> str:
        text = escape(self.text)
        return f'<span style="{s}">{text}</span>' if (s := self.style) else text


def resolve_attr(key: str, value: str) -> Any:
    if key in {"size", "stroke_width"}:
        return int(value)

    if key in {"color", "stroke_fill"}:
        if COLOR_TUPLE_RE.match(value):
            color = tuple(int(x.strip()) for x in value[1:-1].split(","))
            if not_satisfy := next((x for x in color if (not 0 <= x <= 255)), None):
                raise ValueError(
                    f"Invalid color value {value}, "
                    f"expecting tuple of 0-255, got {not_satisfy}",
                )
            return color

        return value

    if key in {"fonts"}:
        return value

    raise ValueError(f"Invalid attribute {key} with value {value}")


class ParsingState(Enum):
    GETTING_KEY = auto()
    GETTING_QUOTE_OR_VALUE = auto()
    GETTING_VALUE = auto()


def parse_chunk(attrs: str, text: str) -> TextChunk:
    resolved_attrs: dict[str, Any] = {}

    k_1st_ch_re = re.compile(r"[a-zA-Z_-]")
    k_ch_re = re.compile(r"[a-zA-Z0-9_-]")

    state: ParsingState = ParsingState.GETTING_KEY
    value_escape_next_char = False
    curr_key_buf: list[str] = []
    curr_key_start_index = 0
    curr_quote = ""
    curr_quote_index = 0
    curr_value_buf: list[str] = []

    def resolve_current():
        nonlocal state, curr_quote, curr_quote_index, curr_key_start_index
        key = "".join(curr_key_buf)
        value = "".join(curr_value_buf)
        curr_key_buf.clear()
        curr_key_start_index = 0
        curr_value_buf.clear()
        curr_quote = ""
        curr_quote_index = 0
        state = ParsingState.GETTING_KEY
        resolved_attrs[key] = resolve_attr(key, value)

    for i, char in enumerate(attrs):
        if state is ParsingState.GETTING_KEY:
            if char.isspace():
                if curr_key_buf and (not curr_key_buf[-1].isspace()):
                    curr_key_buf.append(char)
                continue

            if char == "=":
                if curr_key_buf and curr_key_buf[-1].isspace():
                    curr_key_buf.pop()
                if not curr_key_buf:
                    raise ValueError(f"Expected key, got char {char} at index {i}")
                state = ParsingState.GETTING_QUOTE_OR_VALUE
                continue

            if (curr_key_buf and curr_key_buf[-1].isspace()) or (
                not (k_ch_re if curr_key_buf else k_1st_ch_re).match(char)
            ):
                raise ValueError(f"Invalid char {char} found at index {i} in key")

            curr_key_buf.append(char)
            curr_key_start_index = i

        elif state is ParsingState.GETTING_QUOTE_OR_VALUE:
            if char.isspace():
                continue
            if char in {"'", '"'}:
                curr_quote = char
                curr_quote_index = i
            else:
                curr_value_buf.append(char)
            state = ParsingState.GETTING_VALUE

        elif state is ParsingState.GETTING_VALUE:
            if value_escape_next_char:
                value_escape_next_char = False
                curr_value_buf.append(char)
                continue

            if curr_quote:
                if char == "\\":
                    value_escape_next_char = True
                elif char == curr_quote:
                    resolve_current()
                else:
                    curr_value_buf.append(char)
                continue

            if char.isspace():
                resolve_current()
            elif char == "=":
                raise ValueError(f"Unexpected char {char} found at index {i} in value")
            else:
                curr_value_buf.append(char)

    if curr_value_buf:
        resolve_current()

    if curr_key_buf:
        raise ValueError(
            f"Unterminated key `{''.join(curr_key_buf)}` found"
            f" starting at index {curr_key_start_index}",
        )
    if curr_quote:
        raise ValueError(
            f"Unterminated quote {curr_quote} starting at index {curr_quote_index}",
        )

    return TextChunk(text=text, **resolved_attrs)


def parse_ft(text: str) -> list[TextChunk]:
    result: list[TextChunk] = []
    pattern = r"<ft(?P<attrs>.*?)>(?P<text>[\s\S]*?)</ft>"

    last_idx = 0
    for match in re.finditer(pattern, text):
        # 添加标签前的普通文本
        if match.start() > last_idx:
            plain_text = text[last_idx : match.start()]
            if plain_text:
                result.append(TextChunk(plain_text))

        # 添加富文本块
        result.append(parse_chunk(match["attrs"], match["text"]))
        last_idx = match.end()

    # 添加最后的普通文本
    if last_idx < len(text):
        result.append(TextChunk(text[last_idx:]))

    return result


def transform_ft(text: str) -> str:
    return "".join(str(chunk) for chunk in parse_ft(text))

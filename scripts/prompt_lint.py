#!/usr/bin/env python3
"""Lint documented prompt structure and a bounded set of format anti-patterns.

This linter deliberately does not score semantic creativity or predict generation
quality. It checks whether golden examples keep their documented sections and
whether the compiled prompt is bare natural-language prose rather than a
serialized payload.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


REQUIRED_GOLDEN_SECTIONS = [
    "## Source Brief",
    "## Internal Prompt Specification",
    "## Compiled Natural-Language Prompt",
    "## Lint Result",
    "## Control-Critical Sentences",
]
BLOCKED_MARKERS = ("TO" "DO", "PLACE" "HOLDER")
FENCE_OPEN = re.compile(
    r"^(?P<indent>[ ]{0,3})(?P<marker>`{3,}|~{3,})(?P<info>[^\r\n]*)$"
)
H2_HEADING = re.compile(r"^ {0,3}##[ \t]+(?P<title>.*?)[ \t]*$")
RAW_HTML_BLOCK_OPEN = re.compile(
    r"^ {0,3}<(?P<tag>script|pre|style|textarea)(?=[\s>])",
    re.IGNORECASE,
)
RAW_HTML_PROCESSING_OPEN = re.compile(r"^ {0,3}<\?")
RAW_HTML_DECLARATION_OPEN = re.compile(r"^ {0,3}<![A-Z]")
RAW_HTML_CDATA_OPEN = re.compile(r"^ {0,3}<!\[CDATA\[")
RAW_HTML_TYPE6_OPEN = re.compile(
    r"^ {0,3}</?(?:address|article|aside|base|basefont|blockquote|body|caption|"
    r"center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|"
    r"figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|"
    r"legend|li|link|main|menu|menuitem|nav|noframes|ol|optgroup|option|p|"
    r"param|search|section|summary|table|tbody|td|template|tfoot|th|thead|"
    r"title|tr|track|ul)(?=[ \t\r\n/>]|$)",
    re.IGNORECASE,
)
RAW_HTML_TYPE7_OPEN = re.compile(
    r"^ {0,3}</?[A-Za-z][A-Za-z0-9-]*"
    r"(?:[ \t]+[A-Za-z_:][A-Za-z0-9_.:-]*"
    r"(?:[ \t]*=[ \t]*(?:[^ \t\r\n\"'=<>`]+|'[^']*'|\"[^\"]*\"))?)*"
    r"[ \t]*/?>[ \t]*$"
)
YAML_MAPPING_LINE = re.compile(
    r"^[ \t]*(?:-[ \t]+)?(?P<key>[^\W\d][\w-]*"
    r"(?:[ \t]+[^\W\d][\w-]*)*)[ \t]*[:\uff1a][ \t]*(?P<value>.*)$"
)
YAML_SEQUENCE_LINE = re.compile(r"^[ \t]*-[ \t]+\S.*$")
YAML_BLOCK_VALUE = re.compile(r":[ \t]*[>|][+-]?[ \t]*(?:#.*)?$")
YAML_FLOW_SEQUENCE = re.compile(r"^\[[\s\S]*\][ \t]*(?:#.*)?$")
YAML_QUOTED_MAPPING_LINE = re.compile(
    r"^[ \t]*(?:-[ \t]+)?(?P<quote>[\"'])(?P<key>.*?)"
    r"(?P=quote)[ \t]*[:\uff1a][ \t]*(?P<value>.*)$"
)
YAML_DOCUMENT_START = re.compile(
    r"^(?:---(?:[ \t]+#.*)?|%YAML(?:[ \t]+.*)?)[ \t]*$",
    re.IGNORECASE,
)
MARKDOWN_QUOTE_PREFIX = re.compile(r" {0,3}>[ \t]?")
MARKDOWN_LIST_PREFIX = re.compile(
    r" {0,3}(?:[-+*]|[0-9]{1,9}[.)])[ \t]+"
)
MARKDOWN_TASK_PREFIX = re.compile(r"^\[[ xX]\][ \t]+")
MARKDOWN_HEADING_PREFIX = re.compile(r"^#{1,6}[ \t]+")
MARKDOWN_INLINE_LINK = re.compile(r"!?\[([^\]\r\n]*)\]\([^\)\r\n]*\)")
MARKDOWN_REFERENCE_LINK = re.compile(r"!?\[([^\]\r\n]*)\]\[[^\]\r\n]*\]")
MARKDOWN_PRESENTATION_WRAPPER = re.compile(
    r"^(?P<marker>\*{1,3}|_{1,3}|~~)(?P<body>[\s\S]+)(?P=marker)$"
)
MARKDOWN_CODE_SPAN = re.compile(
    r"^(?P<marker>`+)(?P<body>[^\r\n]+)(?P=marker)$"
)
LEADING_REFERENCE_LABEL = re.compile(
    r"^\[(?P<label>[^\[\]\r\n]{1,120})\](?=[ \t]+\S)"
)
YAML_WRAPPER_KEYS = {
    "prompt", "compiled prompt", "negative prompt", "parameter", "parameters",
    "setting", "settings", "metadata", "input", "output",
    "提示词", "編譯提示詞", "编译提示词", "負面提示詞", "负面提示词",
    "參數", "参数", "設定", "设置", "元數據", "元数据", "輸入", "输入",
    "輸出", "输出", "프롬프트", "컴파일된 프롬프트", "네거티브 프롬프트",
    "매개변수", "설정", "메타데이터", "입력", "출력", "プロンプト",
    "コンパイル済みプロンプト", "ネガティブプロンプト", "パラメータ",
    "設定", "メタデータ", "入力", "出力",
}
PROSE_MAPPING_KEYS = {
    "beginning", "camera", "ending", "finally", "reference", "sound", "then",
}
EMBEDDED_WRAPPER_NOUN = (
    r"(?:array|data(?:[ \t]+array)?|json(?:[ \t]+(?:object|payload))?|"
    r"list|object|payload|serialized(?:[ \t]+(?:data|payload))?|values)"
)
EMBEDDED_PREFIX_WRAPPER = re.compile(
    r"(?:^|[.!?][ \t]+)(?:"
    r"(?:use|provide|return|submit|send|load|input|parse|consume|produce|"
    r"serialize|respond[ \t]+with|reply[ \t]+with|answer[ \t]+with)\b"
    r"[^.!?\r\n]{0,80}\b" + EMBEDDED_WRAPPER_NOUN + r"\b[ \t]*:?"
    r"|(?:here|below)[ \t]+is[ \t]+(?:the[ \t]+)?" + EMBEDDED_WRAPPER_NOUN
    + r"\b[ \t]*:?"
    r"|" + EMBEDDED_WRAPPER_NOUN + r"[ \t]*:"
    r")[ \t]*$",
    re.IGNORECASE,
)
EMBEDDED_SUFFIX_WRAPPER = re.compile(
    r"[ \t]*(?:as|is)[ \t]+(?:the[ \t]+|an?[ \t]+|this[ \t]+)?"
    + EMBEDDED_WRAPPER_NOUN
    + r"\b(?:[ \t]+(?:for|to)[^.!?\r\n]*)?[.!?]?[ \t]*",
    re.IGNORECASE,
)
WHITESPACE_SUFFIX = re.compile(r"[ \t\r\n]*")
ENGLISH_SERIALIZER_CUE = re.compile(
    r"(?:^|[.!?][ \t]+|\r?\n[ \t]*)"
    r"(?:(?:then|now|next|finally)[ \t]*,?[ \t]+)?"
    r"(?:please[ \t]+)?"
    r"(?:answer[ \t]+with|consume|emit|input|load|output|parse|provide|"
    r"produce|reply[ \t]+with|respond[ \t]+with|return|send|serialize|"
    r"submit|use)"
    r"(?:[ \t]+(?:(?:a|an|the|this|that|these|those)[ \t]+)?"
    r"(?:(?:following|below)[ \t]+)?"
    r"(?:(?:serialized[ \t]+)?(?:array|data|json|list|object|payload|"
    r"values|yaml)(?:[ \t]+(?:array|data|list|object|payload|values))?))?"
    r"[ \t]*(?::|=|=>|->)?[ \t]*$",
    re.IGNORECASE,
)
SPANISH_SERIALIZER_CUE = re.compile(
    r"(?:^|[.!?\u00a1\u00bf][ \t]+|\r?\n[ \t]*)"
    r"(?:(?:luego|entonces|ahora|finalmente)[ \t]*,?[ \t]+)?"
    r"(?:por[ \t]+favor[ \t]+)?"
    r"(?:analiza|carga|consume|contesta(?:[ \t]+con)?|devuelve|emite|"
    r"env(?:ia|\u00eda)|entrega|genera|introduce|manda|procesa|produce|"
    r"proporciona|responde(?:[ \t]+con)?|retorna|serializa|usa)"
    r"(?:[ \t]+(?:(?:el|la|los|las|un|una|este|esta|estos|estas)[ \t]+)?"
    r"(?:(?:siguiente|siguientes)[ \t]+)?"
    r"(?:(?:json|yaml)(?:[ \t]+(?:arreglo|carga|datos|lista|matriz|"
    r"objeto|contenido))?|(?:arreglo|carga|datos|lista|matriz|objeto|"
    r"contenido)(?:[ \t]+(?:json|yaml))?))?"
    r"[ \t]*(?::|=|=>|->)?[ \t]*$",
    re.IGNORECASE,
)
CHINESE_SERIALIZER_CUE = re.compile(
    r"(?:^|[.!?\u3002\uff01\uff1f][ \t]*|\r?\n[ \t]*)"
    r"(?:\u7136\u540e|\u63a5\u7740|\u518d|\u6700\u540e|\u73b0\u5728)?[ \t]*"
    r"(?:\u8bf7[ \t]*)?"
    r"(?:(?:\u4ee5|\u6309)[ \t]*(?:json|yaml)[ \t]*(?:\u683c\u5f0f)?[ \t]*)?"
    r"(?:\u8fd4\u56de|\u8f93\u51fa|\u63d0\u4f9b|\u751f\u6210|\u5e8f\u5217\u5316|\u53d1\u9001|\u63d0\u4ea4|\u56de\u590d|\u56de\u7b54|"
    r"\u4f7f\u7528|\u52a0\u8f7d|\u8f93\u5165|\u89e3\u6790|\u8bfb\u53d6|\u5904\u7406)"
    r"(?:[ \t]*(?:\u4ee5\u4e0b|\u4e0b\u5217|\u8fd9\u4e2a|\u8be5|\u6b64))?"
    r"(?:[ \t]*(?:json|yaml)(?:[ \t]*(?:\u5bf9\u8c61|\u6570\u7ec4|\u5217\u8868|\u8f7d\u8377|\u6570\u636e|\u5185\u5bb9))?)?"
    r"[ \t]*(?::|=|=>|->)?[ \t]*$",
    re.IGNORECASE,
)
VISIBLE_STRUCTURE_DISPLAY = re.compile(
    r"\b(?:console|display|interface|monitor|screen|terminal)\b"
    r"[^\r\n]{0,100}\b(?:displays?|prints?|reads?|renders?|shows?)\b"
    r"[ \t]*:?[ \t]*(?:\r?\n[ \t]*)?"
    r"(?:emit|output|provide|produce|serialize|return|send|submit|"
    r"respond[ \t]+with|reply[ \t]+with|answer[ \t]+with)"
    r"[ \t]*(?::|=|=>|->)?[ \t]*$",
    re.IGNORECASE,
)
REFERENCE_ONLY_PREFIX = re.compile(
    r"^\[[^\[\]\r\n]{1,120}\][ \t]*(?:[:\-\u2013\u2014][ \t]*)?$"
)
EXPLICIT_SERIALIZATION_NOUN = re.compile(
    r"(?:array|data(?:[ \t]+array)?|json(?:[ \t]+(?:array|data|list|object|payload))?|"
    r"list|object|payload|serialized(?:[ \t]+(?:data|payload))?|values|yaml|"
    r"arreglo|carga|datos|lista|matriz|objeto|contenido|"
    r"\u5bf9\u8c61|\u6570\u7ec4|\u5217\u8868|\u8f7d\u8377|\u6570\u636e|\u5185\u5bb9)"
    r"[ \t]*(?::|=|=>|->|\uff1a)?[ \t]*$",
    re.IGNORECASE,
)
SERIALIZATION_ONLY_SUFFIX = re.compile(
    r"^[ \t]*(?:[.!?\u3002\uff01\uff1f][ \t]*)?$|"
    r"^[ \t]*(?:,?[ \t]*)?(?:and[ \t]+)?nothing[ \t]+else[.!?]?[ \t]*$|"
    r"^[ \t]*(?:,?[ \t]*)?y[ \t]+nada[ \t]+m(?:a|\u00e1)s[.!?]?[ \t]*$|"
    r"^[ \t]*(?:\uff0c?[ \t]*)?\u4e0d\u8981\u5176\u4ed6\u5185\u5bb9[\u3002\uff01\uff1f]?[ \t]*$",
    re.IGNORECASE,
)
BOUNDARY = (
    "Boundary: checks documented prompt format and anti-patterns; "
    "it does not assess semantic creativity or generation quality."
)


@dataclass(frozen=True)
class FencedBlock:
    label: str
    body: str
    closed: bool


@dataclass(frozen=True)
class MarkdownSection:
    heading: str
    body: str
    line_number: int


class HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.element_stack: list[tuple[str, bool]] = []

    @staticmethod
    def _element_is_hidden(
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> bool:
        if tag.casefold() in {"script", "style", "template"}:
            return True
        normalized = {
            name.casefold(): "" if value is None else value.casefold()
            for name, value in attrs
        }
        style = re.sub(r"\s+", "", normalized.get("style", ""))
        return (
            "hidden" in normalized
            or normalized.get("aria-hidden") == "true"
            or "display:none" in style
            or "visibility:hidden" in style
        )

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        inherited = bool(self.element_stack and self.element_stack[-1][1])
        hidden = inherited or self._element_is_hidden(tag, attrs)
        if tag.casefold() not in {
            "area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr",
        }:
            self.element_stack.append((tag.casefold(), hidden))

    def handle_endtag(self, tag: str) -> None:
        folded = tag.casefold()
        for index in range(len(self.element_stack) - 1, -1, -1):
            if self.element_stack[index][0] == folded:
                del self.element_stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if not self.element_stack or not self.element_stack[-1][1]:
            self.parts.append(data)


class HTMLTableExtractor(HTMLParser):
    """Collect rendered table-cell text without regex-parsing HTML tags."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.saw_table = False
        self.rows: list[list[str]] = []
        self.current_row: list[str] | None = None
        self.current_cell: list[str] | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        del attrs
        folded = tag.casefold()
        if folded == "table":
            self.saw_table = True
        elif folded == "tr":
            self.current_row = []
        elif folded in {"td", "th"} and self.current_row is not None:
            self.current_cell = []

    def handle_data(self, data: str) -> None:
        if self.current_cell is not None:
            self.current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        folded = tag.casefold()
        if folded in {"td", "th"} and self.current_cell is not None:
            if self.current_row is not None:
                self.current_row.append("".join(self.current_cell))
            self.current_cell = None
        elif folded == "tr" and self.current_row is not None:
            self.rows.append(self.current_row)
            self.current_row = None


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def indentation_columns(text: str) -> int:
    columns = 0
    for character in text:
        if character == "\t":
            columns += 4 - (columns % 4)
        else:
            columns += 1
    return columns


def markdown_container_details(
    line: str,
) -> tuple[str, tuple[tuple[str, int], ...]]:
    cursor = 0
    context: list[tuple[str, int]] = []
    while True:
        quote = MARKDOWN_QUOTE_PREFIX.match(line, cursor)
        if quote is not None:
            cursor = quote.end()
            context.append(("quote", 0))
            continue
        list_item = MARKDOWN_LIST_PREFIX.match(line, cursor)
        if list_item is not None:
            context.append(("list", indentation_columns(list_item.group(0))))
            cursor = list_item.end()
            continue
        return line[cursor:], tuple(context)


def indentation_end(
    text: str,
    start: int,
    required_columns: int,
) -> int | None:
    columns = 0
    index = start
    while index < len(text) and text[index] in " \t" and columns < required_columns:
        if text[index] == "\t":
            columns += 4 - (columns % 4)
        else:
            columns += 1
        index += 1
    return index if columns >= required_columns else None


def same_container_content(
    context: tuple[tuple[str, int], ...],
    line: str,
) -> str | None:
    cursor = 0
    for kind, required_columns in context:
        if kind == "quote":
            quote = MARKDOWN_QUOTE_PREFIX.match(line, cursor)
            if quote is None:
                return None
            cursor = quote.end()
        else:
            next_cursor = indentation_end(line, cursor, required_columns)
            if next_cursor is None:
                return None
            cursor = next_cursor
    content = line[cursor:]
    _, extra_context = markdown_container_details(content)
    return content if not extra_context else None


def fence_opener(
    line: str,
) -> tuple[str, str, tuple[tuple[str, int], ...]] | None:
    """Return a CommonMark fence marker and info string, if line opens one."""
    content, context = markdown_container_details(line)
    opened = FENCE_OPEN.fullmatch(content)
    if opened is None:
        return None
    marker = opened.group("marker")
    info = opened.group("info")
    if marker[0] == "`" and "`" in info:
        return None
    return marker, info, context


def is_fence_closer(
    line: str,
    marker_character: str,
    minimum_length: int,
    context: tuple[tuple[str, int], ...],
) -> bool:
    """Recognize only a legal closing fence, including its indentation bound."""
    line = same_container_content(context, line)
    if line is None:
        return False
    leading_spaces = len(line) - len(line.lstrip(" "))
    if leading_spaces > 3:
        return False
    candidate = line[leading_spaces:].rstrip(" \t")
    return (
        len(candidate) >= minimum_length
        and candidate
        and set(candidate) == {marker_character}
    )


def visible_h2_sections(text: str) -> list[MarkdownSection]:
    """Extract real top-level H2 sections outside non-Markdown containers."""
    lines = text.splitlines()
    headings: list[tuple[int, str]] = []
    fence_character: str | None = None
    fence_length = 0
    fence_context: tuple[tuple[str, int], ...] = ()
    in_html_comment = False
    raw_html_tag: str | None = None
    raw_html_until_token: str | None = None
    raw_html_until_blank = False
    block_scalar_indent: int | None = None

    front_matter_end = -1
    if lines and lines[0].lstrip("\ufeff").strip(" \t") == "---":
        front_matter_end = len(lines) - 1
        for index in range(1, len(lines)):
            if lines[index].strip(" \t") in {"---", "..."}:
                front_matter_end = index
                break

    for index, line in enumerate(lines):
        if index <= front_matter_end:
            continue

        # Continue active non-Markdown blocks before looking for new fences.
        # In CommonMark/GFM, fence markers inside HTML comments, raw HTML, or
        # YAML block scalars are literal content and cannot alter parser state.
        if in_html_comment:
            if "-->" in line:
                in_html_comment = False
            continue

        if raw_html_until_token is not None:
            if raw_html_until_token in line:
                raw_html_until_token = None
            continue
        if raw_html_tag is not None:
            if re.search(rf"</{re.escape(raw_html_tag)}[ \t]*>", line, re.IGNORECASE):
                raw_html_tag = None
            continue
        if raw_html_until_blank:
            raw_content = markdown_container_content(line)
            if raw_content.strip(" \t"):
                continue
            raw_html_until_blank = False
            continue

        if block_scalar_indent is not None:
            if not line.strip(" \t"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            if indent > block_scalar_indent or line.startswith("\t"):
                continue
            block_scalar_indent = None

        if fence_character is not None:
            if is_fence_closer(line, fence_character, fence_length, fence_context):
                fence_character = None
                fence_length = 0
                fence_context = ()
            continue

        stripped = line.lstrip(" \t")
        if stripped.startswith("<!--"):
            if "-->" not in stripped[4:]:
                in_html_comment = True
            continue
        if "<!--" in line:
            before, after = line.split("<!--", 1)
            if "-->" in after:
                line = before + after.split("-->", 1)[1]
            else:
                line = before
                in_html_comment = True

        raw_content = markdown_container_content(line)
        token_delimited_html = (
            (RAW_HTML_CDATA_OPEN.match(raw_content), "]]>") ,
            (RAW_HTML_PROCESSING_OPEN.match(raw_content), "?>"),
            (RAW_HTML_DECLARATION_OPEN.match(raw_content), ">"),
        )
        opened_token_block = False
        for opened, closing_token in token_delimited_html:
            if opened is None:
                continue
            if closing_token not in raw_content[opened.end():]:
                raw_html_until_token = closing_token
            opened_token_block = True
            break
        if opened_token_block:
            continue

        raw_open = RAW_HTML_BLOCK_OPEN.match(raw_content)
        if raw_open is not None:
            tag = raw_open.group("tag")
            if re.search(rf"</{re.escape(tag)}[ \t]*>", line, re.IGNORECASE) is None:
                raw_html_tag = tag
            continue
        if (
            RAW_HTML_TYPE6_OPEN.match(raw_content) is not None
            or RAW_HTML_TYPE7_OPEN.match(raw_content) is not None
        ):
            raw_html_until_blank = True
            continue

        if YAML_BLOCK_VALUE.search(line):
            block_scalar_indent = len(line) - len(line.lstrip(" "))
            continue

        opened = fence_opener(line)
        if opened is not None:
            marker, _, fence_context = opened
            fence_character = marker[0]
            fence_length = len(marker)
            continue

        heading = H2_HEADING.fullmatch(line)
        if heading is None:
            continue
        title = re.sub(r"[ \t]+#+[ \t]*$", "", heading.group("title")).strip()
        headings.append((index, f"## {title}"))

    sections: list[MarkdownSection] = []
    for position, (line_index, heading) in enumerate(headings):
        body_end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        sections.append(
            MarkdownSection(
                heading=heading,
                body="\n".join(lines[line_index + 1:body_end]).strip(),
                line_number=line_index + 1,
            )
        )
    return sections


def compiled_prompt(text: str) -> str:
    matches = [
        section.body
        for section in visible_h2_sections(text)
        if section.heading == "## Compiled Natural-Language Prompt"
    ]
    return matches[0] if len(matches) == 1 else ""


def normalized_fence_label(info: str) -> str:
    """Return the first Markdown info-string token in a common normalized form."""
    if not info.strip():
        return ""
    token = info.strip().split(maxsplit=1)[0]
    return token.strip("{}").lstrip(".").lower()


def fenced_blocks(text: str) -> list[FencedBlock]:
    """Extract line-oriented backtick and tilde fences without executing content."""
    lines = text.splitlines()
    blocks: list[FencedBlock] = []
    index = 0
    while index < len(lines):
        opened = fence_opener(lines[index])
        if opened is None:
            index += 1
            continue

        marker, info, context = opened
        marker_char = marker[0]
        minimum_close_length = len(marker)
        label = normalized_fence_label(info)
        body_start = index + 1
        close_index: int | None = None
        cursor = body_start
        while cursor < len(lines):
            if is_fence_closer(
                lines[cursor],
                marker_char,
                minimum_close_length,
                context,
            ):
                close_index = cursor
                break
            cursor += 1

        if close_index is None:
            blocks.append(FencedBlock(label, "\n".join(lines[body_start:]).strip(), False))
            break

        blocks.append(
            FencedBlock(label, "\n".join(lines[body_start:close_index]).strip(), True)
        )
        index = close_index + 1
    return blocks


def json_structure_reason(text: str) -> str | None:
    """Classify a whole object/array candidate with the standard-library parser."""
    candidate = text.lstrip("\ufeff \t\r\n")
    if not candidate or candidate[0] not in "[{":
        return None
    try:
        parsed = json.loads(candidate)
    except (ValueError, RecursionError):
        if candidate[0] == "{":
            return "malformed JSON-like structured data"
        label = LEADING_REFERENCE_LABEL.match(candidate)
        if label is not None and not re.search(r'[,{}"\']', label.group("label")):
            return None
        remainder = candidate[1:].lstrip()
        array_value_start = (
            not remainder
            or remainder[0] in '[{"-0123456789]'
            or remainder.startswith(("true", "false", "null"))
        )
        if array_value_start:
            return "malformed JSON-like structured data"
        # Prompt prose can legitimately begin with a reference label such as
        # ``[Video 1]``. Do not treat every leading square bracket as JSON.
        return None
    if isinstance(parsed, (dict, list)):
        return "structured JSON"
    return None


def direct_serialization_prefix(prefix: str) -> bool:
    """Recognize bounded response-serialization instructions in three languages.

    The cue must end immediately before the structured value.  Optional format
    nouns are accepted, but free-standing phrases such as ``use the following``
    are not: that distinction keeps numbered camera-beat prose out of scope.
    """
    candidate = unicodedata.normalize("NFKC", html.unescape(prefix[-320:]))
    return any(
        pattern.search(candidate) is not None
        for pattern in (
            ENGLISH_SERIALIZER_CUE,
            SPANISH_SERIALIZER_CUE,
            CHINESE_SERIALIZER_CUE,
        )
    )


def explicit_serialization_prefix(prefix: str) -> bool:
    """Return whether the cue names an explicit structured output format."""
    candidate = unicodedata.normalize("NFKC", html.unescape(prefix[-200:]))
    return (
        EXPLICIT_SERIALIZATION_NOUN.search(candidate) is not None
        or re.search(r"\b(?:json|yaml)\b", candidate, re.IGNORECASE) is not None
    )


def sequence_has_natural_tail(text: str, end: int, prefix: str) -> bool:
    """Distinguish an imperative media/list reference from serialized output."""
    suffix = text[end:]
    if SERIALIZATION_ONLY_SUFFIX.fullmatch(suffix) is not None:
        return False
    if EMBEDDED_SUFFIX_WRAPPER.fullmatch(text, end) is not None:
        return False
    if explicit_serialization_prefix(prefix):
        return False
    return bool(suffix.strip())


def serialization_context(text: str, index: int) -> tuple[bool, bool, str]:
    """Return wrapper/direct authority for a structured opener at ``index``."""
    prefix_tail = text[max(0, index - 320):index]
    prefix_wrapper = EMBEDDED_PREFIX_WRAPPER.search(prefix_tail[-160:]) is not None
    direct_serialization = (
        direct_serialization_prefix(prefix_tail)
        and VISIBLE_STRUCTURE_DISPLAY.search(prefix_tail[-240:]) is None
    )
    return prefix_wrapper, direct_serialization, prefix_tail


def next_authorized_structure_start(text: str, start: int, end: int) -> int | None:
    """Find a later cue-backed opener once, without retrying every nested opener."""
    for position in range(start, end):
        if text[position] not in "[{":
            continue
        prefix_wrapper, direct_serialization, _ = serialization_context(text, position)
        if prefix_wrapper or direct_serialization:
            return position
    return None


def balanced_structure_end(text: str, start: int) -> tuple[int, bool]:
    """Return one bracket candidate's end in a single forward pass.

    Nested opening brackets are consumed with their outer candidate instead of
    being retried independently.  This bounds malformed embedded-JSON scanning
    to linear structural work plus one decoder attempt per disjoint candidate.
    """
    pairs = {"[": "]", "{": "}"}
    stack = [pairs[text[start]]]
    in_string = False
    escaped = False
    index = start + 1
    while index < len(text):
        character = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            index += 1
            continue
        if character == '"':
            in_string = True
        elif character in pairs:
            stack.append(pairs[character])
        elif character in "]}":
            if character != stack[-1]:
                return index + 1, False
            stack.pop()
            if not stack:
                return index + 1, True
        index += 1
    return len(text), False


def embedded_json_structure_reason(text: str) -> str | None:
    """Find a complete JSON payload embedded after prose or a reference label."""
    decoder = json.JSONDecoder()
    index = 0
    while index < len(text):
        while index < len(text) and text[index] not in "[{":
            index += 1
        if index >= len(text):
            break
        candidate_end, candidate_closed = balanced_structure_end(text, index)
        prefix_wrapper, direct_serialization, prefix_tail = serialization_context(
            text, index
        )
        try:
            parsed, end = decoder.raw_decode(text, index)
        except (ValueError, RecursionError):
            if prefix_wrapper or direct_serialization:
                embedded_candidate = text[index:candidate_end].strip()
                malformed_reason = json_structure_reason(embedded_candidate)
                if malformed_reason == "malformed JSON-like structured data":
                    return "malformed embedded JSON-like structured data"
                # An unquoted YAML flow sequence can be valid YAML while being
                # invalid JSON (for example ``Return [prompt].``). Strip only a
                # terminal prose mark introduced by the direct cue, then apply
                # the same flow-shape contract used for whole candidates.
                yaml_candidate = re.sub(
                    r"[.!?][ \t]*$", "", embedded_candidate
                )
                if (
                    yaml_structure_reason(yaml_candidate) is not None
                    and not (
                        direct_serialization
                        and not prefix_wrapper
                        and sequence_has_natural_tail(
                            text, candidate_end, prefix_tail
                        )
                    )
                ):
                    return "embedded YAML-like structured data"
            if not candidate_closed:
                authorized = next_authorized_structure_start(
                    text, index + 1, candidate_end
                )
                if authorized is not None:
                    index = authorized
                    continue
            index = max(candidate_end, index + 1)
            continue
        if not isinstance(parsed, (dict, list)):
            index = max(end, index + 1)
            continue
        suffix_wrapper = EMBEDDED_SUFFIX_WRAPPER.fullmatch(text, end) is not None
        suffix_is_empty = WHITESPACE_SUFFIX.fullmatch(text, end) is not None
        bounded_reference_prefix = text[:index].strip() if index <= 256 else ""
        reference_wrapped = (
            suffix_is_empty
            and REFERENCE_ONLY_PREFIX.fullmatch(bounded_reference_prefix) is not None
        )
        direct_authorized = direct_serialization and not (
            isinstance(parsed, list)
            and sequence_has_natural_tail(text, end, prefix_tail)
        )
        if (
            prefix_wrapper
            or suffix_wrapper
            or direct_authorized
            or reference_wrapped
        ):
            return "embedded structured JSON"
        index = max(end, index + 1)
    return None


def normalized_yaml_key(key: str) -> str:
    folded = unicodedata.normalize("NFKC", key).casefold()
    return " ".join(re.sub(r"[-_]", " ", folded).split())


def yaml_mapping_entry(line: str) -> tuple[str, str] | None:
    for pattern in (YAML_MAPPING_LINE, YAML_QUOTED_MAPPING_LINE):
        match = pattern.fullmatch(line)
        if match is not None:
            return normalized_yaml_key(match.group("key")), match.group("value")
    return None


def prose_mapping_label(line: str, normalized_key: str) -> bool:
    """Recognize documented title-case production labels, not YAML fields."""
    match = YAML_MAPPING_LINE.fullmatch(line)
    if match is None:
        return False
    raw_key = unicodedata.normalize("NFKC", match.group("key")).strip()
    first_cased = next((character for character in raw_key if character.isalpha()), "")
    return (
        normalized_key in PROSE_MAPPING_KEYS
        and bool(first_cased)
        and first_cased.isupper()
    )


def yaml_structure_reason(text: str) -> str | None:
    """Detect clear YAML shapes conservatively, without a YAML dependency.

    A colon in ordinary prose is not enough. The detector requires a YAML
    document marker, a block-scalar value, or repeated mapping/sequence lines.
    """
    significant = [line for line in text.splitlines() if line.strip()]
    if not significant:
        return None
    stripped = text.strip("\ufeff \t\r\n")
    if YAML_FLOW_SEQUENCE.fullmatch(stripped):
        return "YAML-like structured data"
    if YAML_DOCUMENT_START.match(significant[0].lstrip()):
        return "YAML-like structured data"
    entry_lines = [
        (entry, line)
        for line in significant
        if (entry := yaml_mapping_entry(line)) is not None
    ]
    entries = [entry for entry, _ in entry_lines]
    wrapper_keys = {normalized_yaml_key(key) for key in YAML_WRAPPER_KEYS}
    if any(key in wrapper_keys for key, _ in entries):
        return "YAML-like structured data"
    if any(YAML_BLOCK_VALUE.search(line) for line in significant):
        return "YAML-like structured data"

    sequence_count = sum(bool(YAML_SEQUENCE_LINE.fullmatch(line)) for line in significant)
    if sequence_count >= 2 or (sequence_count and entries):
        return "YAML-like structured data"
    if len(entries) >= 2 and not all(
        prose_mapping_label(line, key)
        for ((key, _), line) in entry_lines
    ):
        return "YAML-like structured data"
    return None


def markdown_container_content(line: str) -> str:
    """Expose a line's payload after quote/list wrappers for structure checks."""
    content, _ = markdown_container_details(line)
    return content


def presentation_candidate(text: str) -> str:
    """Expose a whole rendered payload without erasing JSON/YAML delimiters."""
    candidate = unicodedata.normalize("NFKC", html.unescape(text)).strip()
    if "<" in candidate and ">" in candidate:
        extractor = HTMLTextExtractor()
        try:
            extractor.feed(candidate)
            extractor.close()
            rendered = "".join(extractor.parts).strip()
            if rendered:
                candidate = rendered
        except (ValueError, TypeError):
            pass

    candidate = MARKDOWN_INLINE_LINK.sub(r"\1", candidate)
    candidate = MARKDOWN_REFERENCE_LINK.sub(r"\1", candidate)
    candidate = re.sub(
        r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])",
        r"\1",
        candidate,
    ).strip()
    candidate = MARKDOWN_HEADING_PREFIX.sub("", candidate, count=1)
    candidate = MARKDOWN_TASK_PREFIX.sub("", candidate, count=1)
    if candidate.startswith("|") and candidate.endswith("|"):
        candidate = candidate.strip(" \t|")

    while True:
        wrapped = (
            MARKDOWN_PRESENTATION_WRAPPER.fullmatch(candidate)
            or MARKDOWN_CODE_SPAN.fullmatch(candidate)
        )
        if wrapped is None:
            break
        candidate = wrapped.group("body").strip()
    return candidate


def html_table_structure_reason(text: str) -> str | None:
    """Reject an HTML table before rendered-text extraction erases its cells."""
    table = HTMLTableExtractor()
    try:
        table.feed(unicodedata.normalize("NFKC", html.unescape(text)))
        table.close()
    except (ValueError, TypeError):
        return None
    return "HTML table wrapper" if table.saw_table else None


MARKDOWN_TABLE_DELIMITER_CELL = re.compile(r"^:?-{3,}:?$")


def markdown_table_cells(line: str) -> list[str] | None:
    """Split a GFM table row at every unescaped pipe.

    GFM discovers table cells before inline code spans are parsed, so backtick
    runs do not protect a pipe.  A backslash escape does, including inside a
    code span.
    """
    content = markdown_container_content(line).strip()
    if "|" not in content:
        return None
    cells: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(content):
        character = content[index]
        if character == "|":
            preceding_backslashes = 0
            for previous in reversed(current):
                if previous != "\\":
                    break
                preceding_backslashes += 1
            if preceding_backslashes % 2 == 0:
                cells.append("".join(current).strip())
                current = []
                index += 1
                continue
        current.append(character)
        index += 1
    cells.append("".join(current).strip())
    if cells and not cells[0]:
        cells.pop(0)
    if cells and not cells[-1]:
        cells.pop()
    if len(cells) < 2:
        return None
    return cells


def markdown_table_structure_reason(text: str) -> str | None:
    """Reject a GFM header/delimiter pair before pipes are normalized away."""
    lines = text.splitlines()
    for header_line, delimiter_line in zip(lines, lines[1:]):
        if not header_line.strip() or not delimiter_line.strip():
            continue
        header = markdown_table_cells(header_line)
        delimiter = markdown_table_cells(delimiter_line)
        if (
            header is not None
            and delimiter is not None
            and len(header) == len(delimiter)
            and all(header)
            and all(MARKDOWN_TABLE_DELIMITER_CELL.fullmatch(cell) for cell in delimiter)
        ):
            return "Markdown table wrapper"
    return None


def bare_structure_reason(text: str) -> str | None:
    table_reason = html_table_structure_reason(text)
    if table_reason:
        return table_reason
    markdown_table_reason = markdown_table_structure_reason(text)
    if markdown_table_reason:
        return markdown_table_reason
    rendered_lines = "\n".join(
        presentation_candidate(markdown_container_content(line))
        for line in text.splitlines()
    )
    for candidate in dict.fromkeys(
        (text, presentation_candidate(text), rendered_lines)
    ):
        whole_reason = (
            json_structure_reason(candidate)
            or embedded_json_structure_reason(candidate)
            or yaml_structure_reason(candidate)
        )
        if whole_reason:
            return whole_reason
    for line in text.splitlines():
        content = markdown_container_content(line)
        for candidate in dict.fromkeys((content, presentation_candidate(content))):
            line_reason = (
                json_structure_reason(candidate)
                or yaml_structure_reason(candidate)
            )
            if line_reason:
                return line_reason
    return None


def is_default_ignorable(character: str) -> bool:
    """Cover format controls plus non-Cf default-ignorable variation marks."""
    codepoint = ord(character)
    return (
        unicodedata.category(character) == "Cf"
        or codepoint == 0x034F
        or 0x180B <= codepoint <= 0x180F
        or 0xFE00 <= codepoint <= 0xFE0F
        or 0xE0100 <= codepoint <= 0xE01EF
    )


def normalized_declaration_line(line: str) -> str:
    """Remove presentation wrappers while preserving declaration semantics."""
    extractor = HTMLTextExtractor()
    try:
        extractor.feed(line)
        extractor.close()
        rendered = "".join(extractor.parts)
    except (ValueError, TypeError):
        rendered = line
    candidate = unicodedata.normalize("NFKC", html.unescape(rendered)).strip()
    candidate = "".join(
        character
        for character in candidate
        if not is_default_ignorable(character)
    )
    candidate = re.sub(
        r"!?\[([^\]\r\n]*)\]\([^\)\r\n]*\)",
        r"\1",
        candidate,
    )
    candidate = re.sub(
        r"!?\[([^\]\r\n]*)\]\[[^\]\r\n]*\]",
        r"\1",
        candidate,
    )
    candidate = re.sub(
        r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])",
        r"\1",
        candidate,
    )
    candidate = re.sub(r"^(?:>[ \t]*)+", "", candidate)
    candidate = re.sub(
        r"^(?:#{1,6}|[-+*]|[0-9]{1,9}[.)])[ \t]+",
        "",
        candidate,
    )
    candidate = candidate.strip(" \t|[](){}<>")
    candidate = re.sub(r"[*_`~]+", "", candidate)
    return candidate.strip(" \t|[](){}<>")


def declaration_tokens(text: str) -> list[str]:
    """Return word tokens after presentation and zero-width normalization."""
    return [
        token.casefold()
        for token in re.findall(r"[^\W_]+", normalized_declaration_line(text))
    ]


def declares_lint_pass(text: str) -> bool:
    """Recognize a pass assertion independent of result/status word order."""
    tokens = declaration_tokens(text)
    if tokens[:1] == ["the"]:
        tokens = tokens[1:]
    while tokens[:1] and tokens[0] in {"computed", "final", "verification"}:
        tokens = tokens[1:]

    if tokens in (
        ["lint", "pass"],
        ["lint", "result", "pass"],
        ["lint", "status", "pass"],
    ):
        return True
    if tokens[:1] and tokens[0] in {"result", "status"}:
        tokens = tokens[1:]
        if tokens[:1] == ["is"]:
            tokens = tokens[1:]
        while tokens[:1] and tokens[0] in {"computed", "final", "verification"}:
            tokens = tokens[1:]
        return tokens == ["lint", "pass"]
    return False


def table_cells_declare_pass(cells: list[str]) -> bool:
    return declares_lint_pass(" ".join(cells))


def declaration_windows(text: str) -> list[str]:
    """Return bounded adjacent visible-line windows for fragmented markup."""
    lines = text.splitlines()
    windows: list[str] = []
    for start, line in enumerate(lines):
        if not line.strip():
            continue
        parts: list[str] = []
        for line in lines[start:start + 3]:
            if not line.strip():
                break
            parts.append(line)
            windows.append("\n".join(parts))
    return windows


def contains_self_declared_pass(text: str) -> bool:
    extractor = HTMLTextExtractor()
    try:
        extractor.feed(text)
        extractor.close()
        rendered = "".join(extractor.parts)
    except (ValueError, TypeError):
        rendered = text

    for variant in dict.fromkeys((text, rendered)):
        for candidate in declaration_windows(variant):
            if declares_lint_pass(candidate):
                return True
        for line in variant.splitlines():
            cells = markdown_table_cells(line)
            if cells is not None and table_cells_declare_pass(cells):
                return True

    table = HTMLTableExtractor()
    try:
        table.feed(text)
        table.close()
    except (ValueError, TypeError):
        pass
    if any(table_cells_declare_pass(row) for row in table.rows):
        return True
    return False


def structured_prompt_reason(prompt: str, *, strict: bool = False) -> str | None:
    """Return a bounded format violation, or ``None`` for natural-language prose."""
    blocks = fenced_blocks(prompt)
    for block in blocks:
        if block.label == "json":
            if not block.closed:
                return "malformed JSON code fence"
            try:
                json.loads(block.body)
            except (ValueError, RecursionError):
                return "malformed JSON in a labeled code fence"
            return "structured JSON in a labeled code fence"

        if block.label in {"yaml", "yml"}:
            if not block.closed:
                return "malformed YAML code fence"
            return "structured YAML-like data in a labeled code fence"

        nested_reason = bare_structure_reason(block.body)
        if nested_reason:
            return f"{nested_reason} in a code fence"

    if strict and blocks:
        return "code fence wrapper; strict mode requires bare natural-language prose"

    return bare_structure_reason(prompt)


def lint_markdown(path: Path, root: Path, *, strict: bool = False) -> list[str]:
    rel = path.relative_to(root).as_posix()
    try:
        text = read_text(path)
    except (OSError, UnicodeError) as exc:
        return [f"{rel}: cannot read UTF-8 Markdown: {type(exc).__name__}"]
    errors: list[str] = []

    if any(marker in text for marker in BLOCKED_MARKERS):
        errors.append(f"{rel}: contains blocked draft marker")

    if "golden-prompts" in rel:
        sections = visible_h2_sections(text)
        section_groups = {
            heading: [section for section in sections if section.heading == heading]
            for heading in REQUIRED_GOLDEN_SECTIONS
        }
        for section in REQUIRED_GOLDEN_SECTIONS:
            count = len(section_groups[section])
            if count == 0:
                errors.append(f"{rel}: missing {section}")
            elif count > 1:
                errors.append(f"{rel}: duplicate {section}")
        ordered_required = [
            section.heading
            for section in sections
            if section.heading in REQUIRED_GOLDEN_SECTIONS
        ]
        if all(len(section_groups[heading]) == 1 for heading in REQUIRED_GOLDEN_SECTIONS):
            if ordered_required != REQUIRED_GOLDEN_SECTIONS:
                errors.append(f"{rel}: golden prompt sections are out of order")

        prompt_sections = section_groups["## Compiled Natural-Language Prompt"]
        prompt = prompt_sections[0].body if len(prompt_sections) == 1 else ""
        if not prompt:
            errors.append(f"{rel}: missing compiled natural-language prompt")
        else:
            reason = structured_prompt_reason(prompt, strict=strict)
            if reason:
                errors.append(
                    f"{rel}: compiled prompt must be natural language, not {reason}"
                )
        if strict and contains_self_declared_pass(text):
            errors.append(
                f"{rel}: self-declared `lint: pass` is not computed evidence; "
                "run this linter for the result"
            )
        control_sections = section_groups["## Control-Critical Sentences"]
        if (
            len(control_sections) != 1
            or "why this remains" not in control_sections[0].body.lower()
        ):
            errors.append(f"{rel}: missing control-critical explanation")

    return errors


def scan(root: Path, *, strict: bool = False) -> list[str]:
    errors: list[str] = []
    for base in [root / "examples"]:
        if not base.exists():
            errors.append(f"missing {base.relative_to(root).as_posix()}")
            continue
        for path in base.rglob("*.md"):
            errors.extend(lint_markdown(path, root, strict=strict))
    return errors


def self_test() -> list[str]:
    cases = [
        (
            "ordinary prose",
            "Beginning: hold the accepted frame. Then: stop at the door.",
            False,
            False,
        ),
        ("JSON object", '{"prompt": "stop at the door"}', False, True),
        ("JSON array", '[{"prompt": "stop at the door"}]', False, True),
        ("YAML flow sequence", "[prompt, camera]", False, True),
        ("fenced JSON", "```json\n{\"prompt\": \"x\"}\n```", False, True),
        ("YAML mapping", "prompt: stop at door\ncamera: locked", False, True),
        ("fenced prose default", "```text\nStop at the door.\n```", False, False),
        ("fenced prose strict", "```text\nStop at the door.\n```", True, True),
    ]
    errors: list[str] = []
    for name, prompt, strict, expected_violation in cases:
        detected = structured_prompt_reason(prompt, strict=strict) is not None
        if detected != expected_violation:
            errors.append(
                f"self-test failed: {name} expected violation={expected_violation}, "
                f"got {detected}"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Lint golden prompt document structure and serialized-format anti-patterns. "
            "This does not score creativity or generation quality."
        )
    )
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "require bare compiled prose and reject self-declared `lint: pass` claims; "
            "default mode permits prose-only code fences for compatibility"
        ),
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    errors = self_test() if args.self_test else []
    root = Path(args.repo).resolve()
    errors.extend(scan(root, strict=args.strict))

    if errors:
        print("Prompt structure lint errors:")
        for error in errors:
            print(f"- {error}")
        print(BOUNDARY)
        return 1
    print("Prompt structure lint passed.")
    print(BOUNDARY)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

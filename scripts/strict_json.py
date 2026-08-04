#!/usr/bin/env python3
"""Bounded, dependency-free JSON and JSONL input helpers.

The standard-library decoder deliberately accepts duplicate object keys and
non-finite numbers. Those extensions are unsafe for repository validation:
two consumers can disagree about which value is authoritative, and a file can
pass Python checks while remaining invalid JSON for another tool.

The public limits leave wide headroom over the shipped fixtures while bounding
CPU and memory exposure: 4 MiB per input, 128 nesting levels, 1,024 characters
per number, 512 KiB per JSONL record, and 10,000 JSONL records. JSONL recognizes
only LF and CRLF record endings. Blank physical records are rejected; every
reported JSONL line number therefore counts real LF characters only.

All repository JSON readers use this module so the integrity contract is
identical in a checkout, an unpacked archive, and an installed skill. Repository
inputs reject every linked path component (POSIX symbolic links and Windows
junction/reparse points) plus lexical or resolved root escapes. Dynamic CLI
diagnostics are rendered as bounded, single-line ASCII with unsafe code points
preserved as escapes, including on strict CP1252 consoles.
"""
from __future__ import annotations

import json
import math
import os
import re
import stat
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import UnionType
from typing import Any, get_args


MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_JSON_DEPTH = 128
MAX_NUMBER_CHARS = 1024
MAX_JSONL_LINE_BYTES = 512 * 1024
MAX_JSONL_RECORDS = 10_000
MAX_DIAGNOSTIC_CHARS = 512
MAX_DIAGNOSTIC_KEY_CHARS = 48
MAX_DIAGNOSTIC_COUNT = 50
MAX_DIAGNOSTIC_TOTAL_CHARS = 16_384
READ_CHUNK_BYTES = 64 * 1024

ExpectedType = type[Any] | tuple[type[Any], ...] | UnionType
_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")


def _sanitize_diagnostic(text: str, limit: int = MAX_DIAGNOSTIC_CHARS) -> str:
    """Escape line/control characters and cap user-controlled diagnostics."""

    limit = max(0, limit)
    escaped: list[str] = []
    length = 0
    for char in text:
        codepoint = ord(char)
        if char == "\n":
            piece = r"\n"
        elif char == "\r":
            piece = r"\r"
        elif char == "\t":
            piece = r"\t"
        elif codepoint < 0x20 or codepoint > 0x7E:
            if codepoint <= 0xFFFF:
                piece = f"\\u{codepoint:04x}"
            else:
                piece = f"\\U{codepoint:08x}"
        else:
            piece = char
        if length + len(piece) > limit:
            escaped.append("..."[: max(0, limit - length)])
            break
        escaped.append(piece)
        length += len(piece)
    return "".join(escaped)


def diagnostic_text(value: object, limit: int = MAX_DIAGNOSTIC_CHARS) -> str:
    """Return bounded, single-line, ASCII-safe user-controlled text."""

    return _sanitize_diagnostic(str(value), limit)


def diagnostic_path(path: str | Path) -> str:
    """Render a filesystem path without console or line-injection hazards."""

    return diagnostic_text(Path(path).as_posix())


def diagnostic_json_path(parts: Any) -> str:
    """Render an iterable as an ASCII-safe RFC 6901-style JSON pointer."""

    rendered: list[str] = []
    for part in parts:
        safe = diagnostic_text(part, 96).replace("~", "~0").replace("/", "~1")
        rendered.append(safe)
    return "/" + "/".join(rendered)


def _diagnostic_key(key: str) -> str:
    fragment = key[:MAX_DIAGNOSTIC_KEY_CHARS]
    rendered = repr(fragment)
    if len(key) > MAX_DIAGNOSTIC_KEY_CHARS:
        rendered += "..."
    return _sanitize_diagnostic(rendered, 320)


class StrictJSONError(ValueError):
    """A bounded JSON integrity error with optional source coordinates."""

    def __init__(
        self,
        message: str,
        *,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        self.message = _sanitize_diagnostic(message)
        self.line = line
        self.column = column
        super().__init__(str(self))

    def __str__(self) -> str:
        if self.line is None:
            return self.message
        if self.column is None:
            return f"{self.message} at line {self.line}"
        return f"{self.message} at line {self.line} column {self.column}"


class _DuplicateKey(ValueError):
    def __init__(self, key: str) -> None:
        self.key = key


class _NonFiniteNumber(ValueError):
    def __init__(self, token: str) -> None:
        self.token = token


class _NumberParseFailure(ValueError):
    def __init__(self, token: str) -> None:
        self.token = token


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise _DuplicateKey(key)
        obj[key] = value
    return obj


def _reject_constant(token: str) -> Any:
    raise _NonFiniteNumber(token)


def _parse_finite_float(token: str) -> float:
    try:
        value = float(token)
    except (OverflowError, ValueError):
        raise _NumberParseFailure(token) from None
    if not math.isfinite(value):
        raise _NonFiniteNumber(token)
    return value


def _parse_finite_decimal(token: str) -> Decimal:
    """Preserve an exact finite token for lineage-sensitive consumers."""

    try:
        value = Decimal(token)
        float_value = float(token)
    except (InvalidOperation, OverflowError, ValueError):
        raise _NumberParseFailure(token) from None
    if not value.is_finite() or not math.isfinite(float_value):
        raise _NonFiniteNumber(token)
    return value


def _parse_bounded_int(token: str) -> int:
    try:
        return int(token)
    except (OverflowError, ValueError):
        raise _NumberParseFailure(token) from None


def _line_column(text: str, offset: int) -> tuple[int, int]:
    prefix = text[:offset]
    return prefix.count("\n") + 1, len(prefix.rsplit("\n", 1)[-1]) + 1


def _token_position(text: str, token: str) -> tuple[int, int] | tuple[None, None]:
    """Locate a token while ignoring identical text inside strings."""

    in_string = False
    escaped = False
    index = 0
    while index < len(text):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            index += 1
            continue
        if text.startswith(token, index):
            return _line_column(text, index)
        index += 1
    return None, None


def _validate_lexical_bounds(text: str) -> tuple[int, int | None]:
    """Bound nesting and numeric work before invoking the recursive decoder."""

    depth = 0
    deepest_offset = 0
    first_number_offset: int | None = None
    in_string = False
    escaped = False
    index = 0
    while index < len(text):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            index += 1
            continue
        if char in "{[":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                line, column = _line_column(text, index)
                raise StrictJSONError(
                    f"maximum JSON nesting depth is {MAX_JSON_DEPTH}",
                    line=line,
                    column=column,
                )
            deepest_offset = index
            index += 1
            continue
        if char in "}]":
            depth = max(0, depth - 1)
            index += 1
            continue
        if char == "-" or char.isdigit():
            match = _NUMBER.match(text, index)
            if match:
                token_length = match.end() - index
                if first_number_offset is None:
                    first_number_offset = index
                if token_length > MAX_NUMBER_CHARS:
                    line, column = _line_column(text, index)
                    raise StrictJSONError(
                        f"JSON number exceeds {MAX_NUMBER_CHARS} characters",
                        line=line,
                        column=column,
                    )
                index = match.end()
                continue
        index += 1
    return deepest_offset, first_number_offset


def _duplicate_key_position(
    text: str,
    duplicate_key: str,
) -> tuple[int, int] | tuple[None, None]:
    """Locate the repeated key inside its object for a useful diagnostic."""

    stack: list[dict[str, Any]] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if char == "{":
            stack.append({"kind": "object", "keys": set(), "expects_key": True})
            index += 1
            continue
        if char == "[":
            stack.append({"kind": "array"})
            index += 1
            continue
        if char in "}]":
            if stack:
                stack.pop()
            index += 1
            continue
        if char == ",":
            if stack and stack[-1]["kind"] == "object":
                stack[-1]["expects_key"] = True
            index += 1
            continue
        if char != '"':
            index += 1
            continue

        start = index
        try:
            value, index = json.decoder.scanstring(text, index + 1, True)
        except ValueError:
            return None, None
        if not stack or stack[-1]["kind"] != "object" or not stack[-1]["expects_key"]:
            continue
        lookahead = index
        while lookahead < len(text) and text[lookahead].isspace():
            lookahead += 1
        if lookahead >= len(text) or text[lookahead] != ":":
            continue
        keys = stack[-1]["keys"]
        if value == duplicate_key and value in keys:
            return _line_column(text, start)
        keys.add(value)
        stack[-1]["expects_key"] = False
    return None, None


def _surrogate_position(text: str) -> tuple[int, int] | tuple[None, None]:
    index = 0
    while index < len(text):
        if text[index] != '"':
            index += 1
            continue
        start = index
        try:
            value, index = json.decoder.scanstring(text, index + 1, True)
        except ValueError:
            return None, None
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            return _line_column(text, start)
    return None, None


def _json_type_name(value_or_type: Any) -> str:
    value_type = value_or_type if isinstance(value_or_type, type) else type(value_or_type)
    return {
        dict: "object",
        list: "array",
        str: "string",
        int: "number",
        float: "number",
        bool: "boolean",
        type(None): "null",
    }.get(value_type, value_type.__name__)


def _normalize_expected_types(expected_type: ExpectedType) -> tuple[type[Any], ...]:
    if isinstance(expected_type, tuple):
        types = expected_type
    elif isinstance(expected_type, UnionType):
        types = get_args(expected_type)
    elif isinstance(expected_type, type):
        types = (expected_type,)
    else:
        raise TypeError("expected_type must be a type, tuple of types, or PEP 604 union")
    if not types or any(not isinstance(item, type) for item in types):
        raise TypeError("expected_type union must contain one or more concrete types")
    return types


def _expected_name(expected_types: tuple[type[Any], ...]) -> str:
    names: list[str] = []
    for item in expected_types:
        name = _json_type_name(item)
        if name not in names:
            names.append(name)
    return " or ".join(names)


def _path_for_key(location: str, key: str) -> str:
    return f"{location}[{_diagnostic_key(key)}]"


def _check_surrogates(value: Any, location: str = "$") -> None:
    if isinstance(value, str):
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise StrictJSONError(f"unpaired Unicode surrogate at {location}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_surrogates(item, f"{location}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _check_surrogates(key, f"{location}.<key>")
            _check_surrogates(item, _path_for_key(location, key))


def _enforce_text_size(text: str, label: str) -> None:
    if len(text) > MAX_JSON_BYTES:
        raise StrictJSONError(
            f"{label} exceeds {MAX_JSON_BYTES} bytes", line=1, column=1
        )
    size = len(text.encode("utf-8", errors="surrogatepass"))
    if size > MAX_JSON_BYTES:
        raise StrictJSONError(
            f"{label} exceeds {MAX_JSON_BYTES} bytes", line=1, column=1
        )


def _file_signature(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    """Identity plus mutation-sensitive metadata for one opened file."""

    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        getattr(metadata, "st_mtime_ns", int(metadata.st_mtime * 1_000_000_000)),
        getattr(metadata, "st_ctime_ns", int(metadata.st_ctime * 1_000_000_000)),
    )


def _verify_opened_repo_file(
    root: Path,
    path: Path,
    opened: os.stat_result,
    label: str,
) -> None:
    """Bind an opened handle to the still-contained, non-reparse path."""

    checked = validate_repo_input_path(root, path)
    try:
        current = os.stat(checked, follow_symlinks=False)
    except OSError as exc:
        reason = diagnostic_text(exc.strerror or type(exc).__name__, 160)
        raise StrictJSONError(
            f"cannot inspect opened {label} {diagnostic_path(path)}: {reason}"
        ) from None

    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    attributes = getattr(current, "st_file_attributes", 0)
    if stat.S_ISLNK(current.st_mode) or attributes & reparse_flag:
        raise StrictJSONError(
            "repository input uses a symbolic link, junction, or reparse point: "
            f"{diagnostic_path(path)}"
        )
    if not stat.S_ISREG(current.st_mode):
        raise StrictJSONError(
            f"{label} is not a regular file: {diagnostic_path(path)}"
        )
    if not os.path.samestat(opened, current):
        raise StrictJSONError(
            f"repository input changed identity while being opened: "
            f"{diagnostic_path(path)}"
        )


def _read_bounded(path: Path, label: str, *, root: Path | None = None) -> bytes:
    """Read one regular file through a single bounded, identity-checked handle."""

    checked = validate_repo_input_path(root, path) if root is not None else path
    try:
        preopened = os.stat(checked, follow_symlinks=False)
    except OSError as exc:
        reason = diagnostic_text(exc.strerror or type(exc).__name__, 160)
        raise StrictJSONError(
            f"cannot inspect {label} {diagnostic_path(path)}: {reason}"
        ) from None
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    preopened_attributes = getattr(preopened, "st_file_attributes", 0)
    if stat.S_ISLNK(preopened.st_mode) or preopened_attributes & reparse_flag:
        raise StrictJSONError(
            "repository input uses a symbolic link, junction, or reparse point: "
            f"{diagnostic_path(path)}"
        )
    if not stat.S_ISREG(preopened.st_mode):
        raise StrictJSONError(
            f"{label} is not a regular file: {diagnostic_path(path)}"
        )
    if preopened.st_size > MAX_JSON_BYTES:
        raise StrictJSONError(
            f"{label} exceeds {MAX_JSON_BYTES} bytes", line=1, column=1
        )
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_CLOEXEC", 0)
    # A FIFO opened read-only can wait forever for a writer before ``fstat``
    # gets a chance to reject it.  Non-blocking mode is inert for regular
    # files and makes special files return from ``open`` promptly so the
    # regular-file boundary below can fail closed.
    flags |= getattr(os, "O_NONBLOCK", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(checked, flags)
        opened = os.fstat(descriptor)
        attributes = getattr(opened, "st_file_attributes", 0)
        if not stat.S_ISREG(opened.st_mode):
            raise StrictJSONError(
                f"{label} is not a regular file: {diagnostic_path(path)}"
            )
        if attributes & reparse_flag:
            raise StrictJSONError(
                "repository input opened a symbolic link, junction, or reparse point: "
                f"{diagnostic_path(path)}"
            )
        if not os.path.samestat(preopened, opened):
            raise StrictJSONError(
                f"{label} changed identity while being opened: "
                f"{diagnostic_path(path)}"
            )
        if opened.st_size > MAX_JSON_BYTES:
            raise StrictJSONError(
                f"{label} exceeds {MAX_JSON_BYTES} bytes", line=1, column=1
            )
        if root is not None:
            _verify_opened_repo_file(root, path, opened, label)

        chunks: list[bytes] = []
        total = 0
        while total <= MAX_JSON_BYTES:
            chunk = os.read(
                descriptor,
                min(READ_CHUNK_BYTES, MAX_JSON_BYTES + 1 - total),
            )
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
        data = b"".join(chunks)
        if len(data) > MAX_JSON_BYTES:
            raise StrictJSONError(
                f"{label} exceeds {MAX_JSON_BYTES} bytes", line=1, column=1
            )

        closed_over = os.fstat(descriptor)
        if _file_signature(opened) != _file_signature(closed_over):
            raise StrictJSONError(
                f"{label} changed while being read: {diagnostic_path(path)}"
            )
        if root is not None:
            _verify_opened_repo_file(root, path, closed_over, label)
        return data
    except StrictJSONError:
        raise
    except OSError as exc:
        reason = diagnostic_text(exc.strerror or type(exc).__name__, 160)
        raise StrictJSONError(
            f"cannot read {label} {diagnostic_path(path)}: {reason}"
        ) from None
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


def validate_repo_input_path(root: Path, path: Path) -> Path:
    """Reject linked/reparse input paths and paths resolving outside ``root``."""

    root_lexical = Path(os.path.abspath(os.fspath(root)))
    path_lexical = Path(os.path.abspath(os.fspath(path)))
    try:
        relative = path_lexical.relative_to(root_lexical)
    except ValueError:
        raise StrictJSONError(
            f"repository input escapes root: {diagnostic_path(path_lexical)}"
        ) from None

    current = root_lexical
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    for part in relative.parts:
        current /= part
        try:
            metadata = os.lstat(current)
        except OSError as exc:
            reason = diagnostic_text(exc.strerror or type(exc).__name__, 160)
            raise StrictJSONError(
                f"cannot inspect repository input {diagnostic_path(relative)}: {reason}"
            ) from None
        attributes = getattr(metadata, "st_file_attributes", 0)
        if stat.S_ISLNK(metadata.st_mode) or attributes & reparse_flag:
            linked = current.relative_to(root_lexical)
            raise StrictJSONError(
                "repository input uses a symbolic link, junction, or reparse point: "
                f"{diagnostic_path(linked)}"
            )

    try:
        resolved_root = root_lexical.resolve(strict=True)
        resolved_path = path_lexical.resolve(strict=True)
    except OSError as exc:
        reason = diagnostic_text(exc.strerror or type(exc).__name__, 160)
        raise StrictJSONError(
            f"cannot resolve repository input {diagnostic_path(relative)}: {reason}"
        ) from None
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError:
        raise StrictJSONError(
            f"repository input resolves outside root: {diagnostic_path(relative)}"
        ) from None
    return path_lexical


def _decode_utf8(data: bytes) -> str:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        prefix = data[: exc.start].decode("utf-8", errors="strict")
        line, column = _line_column(prefix, len(prefix))
        raise StrictJSONError(
            f"malformed UTF-8: {exc.reason}", line=line, column=column
        ) from None
    if text.startswith("\ufeff"):
        raise StrictJSONError("UTF-8 BOM is not permitted", line=1, column=1)
    return text


def loads_json(
    text: str,
    *,
    expected_type: ExpectedType | None = None,
    _exact_numbers: bool = False,
) -> Any:
    """Decode one bounded strict JSON value from text.

    Type checks use exact JSON result types. Pass ``(int, float)`` or
    ``int | float`` when either JSON number representation is intentional;
    ``bool`` never satisfies ``int``.
    """

    _enforce_text_size(text, "JSON input")
    if text.startswith("\ufeff"):
        raise StrictJSONError("UTF-8 BOM is not permitted", line=1, column=1)
    expected_types = (
        _normalize_expected_types(expected_type) if expected_type is not None else None
    )
    deepest_offset, first_number_offset = _validate_lexical_bounds(text)
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
            parse_float=(
                _parse_finite_decimal if _exact_numbers else _parse_finite_float
            ),
            parse_int=_parse_bounded_int,
        )
    except json.JSONDecodeError as exc:
        raise StrictJSONError(exc.msg, line=exc.lineno, column=exc.colno) from None
    except _DuplicateKey as exc:
        line, column = _duplicate_key_position(text, exc.key)
        raise StrictJSONError(
            f"duplicate object key: {_diagnostic_key(exc.key)}",
            line=line,
            column=column,
        ) from None
    except _NonFiniteNumber as exc:
        line, column = _token_position(text, exc.token)
        raise StrictJSONError(
            f"non-finite number is not permitted: {_sanitize_diagnostic(exc.token, 80)}",
            line=line,
            column=column,
        ) from None
    except _NumberParseFailure as exc:
        line, column = _token_position(text, exc.token)
        raise StrictJSONError(
            "JSON number could not be parsed within resource limits",
            line=line,
            column=column,
        ) from None
    except (MemoryError, OverflowError, RecursionError):
        line, column = _line_column(text, deepest_offset)
        raise StrictJSONError(
            "JSON parser resource limit exceeded", line=line, column=column
        ) from None
    except ValueError:
        offset = first_number_offset if first_number_offset is not None else deepest_offset
        line, column = _line_column(text, offset)
        raise StrictJSONError(
            "JSON value could not be parsed within resource limits",
            line=line,
            column=column,
        ) from None

    try:
        _check_surrogates(value)
    except StrictJSONError as exc:
        line, column = _surrogate_position(text)
        raise StrictJSONError(exc.message, line=line, column=column) from None
    if expected_types is not None and type(value) not in expected_types:
        raise StrictJSONError(
            "top-level JSON value must be "
            f"{_expected_name(expected_types)}, got {_json_type_name(value)}",
            line=1,
            column=1,
        )
    return value


def loads_json_bytes(
    data: bytes,
    *,
    expected_type: ExpectedType | None = None,
    _exact_numbers: bool = False,
) -> Any:
    """Decode bounded strict UTF-8 bytes containing one JSON value."""

    if len(data) > MAX_JSON_BYTES:
        raise StrictJSONError(
            f"JSON input exceeds {MAX_JSON_BYTES} bytes", line=1, column=1
        )
    return loads_json(
        _decode_utf8(data),
        expected_type=expected_type,
        _exact_numbers=_exact_numbers,
    )


def load_json(
    path: Path,
    *,
    expected_type: ExpectedType | None = None,
    root: Path | None = None,
    _exact_numbers: bool = False,
) -> Any:
    """Read a path as bounded strict UTF-8 JSON."""

    return loads_json_bytes(
        _read_bounded(path, "JSON input", root=root),
        expected_type=expected_type,
        _exact_numbers=_exact_numbers,
    )


def read_repo_text(root: Path, path: Path) -> str:
    """Read bounded strict UTF-8 text without following repository indirection."""

    return _decode_utf8(_read_bounded(path, "repository text input", root=root))


def _reject_bare_carriage_returns(text: str) -> None:
    index = text.find("\r")
    while index != -1:
        if index + 1 >= len(text) or text[index + 1] != "\n":
            line, column = _line_column(text, index)
            raise StrictJSONError(
                "bare carriage return is not a JSONL record ending",
                line=line,
                column=column,
            )
        index = text.find("\r", index + 1)


def _line_byte_length(text: str) -> int:
    return len(text.encode("utf-8", errors="surrogatepass"))


def load_jsonl(
    path: Path,
    *,
    expected_type: ExpectedType | None = None,
    root: Path | None = None,
) -> list[tuple[int, Any]]:
    """Read LF/CRLF JSON Lines and return values with physical LF line numbers.

    A final LF is allowed. Empty or space/tab-only physical records are not.
    Bare CR and every non-LF Unicode/control separator remain record content,
    so they cannot silently create extra records. Legal raw or escaped U+2028
    inside a JSON string remains valid JSON.
    """

    text = _decode_utf8(_read_bounded(path, "JSONL input", root=root))
    _reject_bare_carriage_returns(text)
    physical_lines = text.split("\n")
    if physical_lines and physical_lines[-1] == "":
        physical_lines.pop()

    records: list[tuple[int, Any]] = []
    for line_number, raw_line in enumerate(physical_lines, start=1):
        line = raw_line[:-1] if raw_line.endswith("\r") else raw_line
        if not line or all(char in " \t" for char in line):
            raise StrictJSONError(
                "blank physical lines are not permitted in JSONL",
                line=line_number,
                column=1,
            )
        if _line_byte_length(line) > MAX_JSONL_LINE_BYTES:
            raise StrictJSONError(
                f"JSONL record exceeds {MAX_JSONL_LINE_BYTES} bytes",
                line=line_number,
                column=1,
            )
        if len(records) >= MAX_JSONL_RECORDS:
            raise StrictJSONError(
                f"JSONL input exceeds {MAX_JSONL_RECORDS} records",
                line=line_number,
                column=1,
            )
        try:
            value = loads_json(line, expected_type=expected_type)
        except StrictJSONError as exc:
            absolute_line = line_number + (exc.line - 1 if exc.line is not None else 0)
            raise StrictJSONError(
                exc.message,
                line=absolute_line,
                column=exc.column,
            ) from None
        records.append((line_number, value))
    return records


# Compatibility names retained for the lineage and project-state consumers.
# They delegate parsing to the hardened implementation above, so every caller
# shares the same duplicate-key, depth, number, UTF-8, and bounded-read policy.
def safe_diagnostic_text(value: str, limit: int = MAX_DIAGNOSTIC_CHARS) -> str:
    return diagnostic_text(value, limit)


def bound_diagnostics(messages: list[str], omission: str) -> list[str]:
    bounded: list[str] = []
    total = 0
    marker = diagnostic_text(omission)

    def finish_with_marker() -> None:
        nonlocal total
        while bounded and total + len(marker) > MAX_DIAGNOSTIC_TOTAL_CHARS:
            total -= len(bounded.pop())
        if (
            len(bounded) < MAX_DIAGNOSTIC_COUNT
            and len(marker) <= MAX_DIAGNOSTIC_TOTAL_CHARS
        ):
            bounded.append(marker)

    for message in messages:
        candidate = diagnostic_text(message)
        if len(bounded) >= MAX_DIAGNOSTIC_COUNT - 1:
            finish_with_marker()
            break
        if total + len(candidate) > MAX_DIAGNOSTIC_TOTAL_CHARS:
            finish_with_marker()
            break
        bounded.append(candidate)
        total += len(candidate)
    return bounded


def loads(text: str) -> Any:
    return loads_json(text, _exact_numbers=True)


def load(path: Path) -> Any:
    return load_json(path, _exact_numbers=True)


def json_integer(value: object) -> int | float | Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return value
    if (
        isinstance(value, Decimal)
        and value.is_finite()
        and value == value.to_integral_value()
    ):
        return value
    return None


def is_json_number(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, Decimal):
        return value.is_finite()
    return False

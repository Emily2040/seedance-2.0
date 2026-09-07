"""Pure ledger text and offline regeneration-command formatting.

No file publication, environment access, scoring or provider calls belong here.
The old scripts.eval_run imports remain aliases for compatibility.
"""
from __future__ import annotations

import html
import re
import shlex
import sys
from pathlib import Path

_EXECUTED_CODE = sys._getframe().f_code
try:
    _EXECUTED_PATH = Path(__file__).resolve(strict=True)
except OSError:
    _EXECUTED_PATH = None
_EXECUTED_SOURCE_SHA256 = "c751ce0ab054fc808b8d31f6693da77099d14c9f38dbfce15f186dde570ffc07"


def _is_utf8_encodable(value: str) -> bool:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _ledger_row_sort_key(indexed_row: tuple[int, object]) -> tuple[int, str, int]:
    index, row = indexed_row
    if not isinstance(row, dict):
        return (2, "", index)
    sequence = row.get("sequence")
    sequence_order = 0 if sequence is False else 1 if sequence is True else 2
    case_id = row.get("id")
    safe_id = (
        case_id
        if isinstance(case_id, str) and _is_utf8_encodable(case_id)
        else ""
    )
    return (sequence_order, safe_id, index)


def _safe_ledger_text(value: str, limit: int = 80) -> str:
    if not _is_utf8_encodable(value):
        return "[invalid Unicode string]"
    # Markdown treats several controls as line boundaries even when ``\n`` is
    # absent. Collapse every unsafe C0/C1 control and Unicode line separator
    # before truncation so one field can never create another ledger line.
    sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]+", " ", value)
    return sanitized.replace("|", "/")[:limit]


def _safe_markdown_code(value: str, limit: int = 80) -> str:
    """Sanitize values interpolated into Markdown code spans or fences."""
    return _safe_ledger_text(value, limit=limit).replace("`", "'")


def _safe_markdown_text(value: str, limit: int = 80) -> str:
    """Make untrusted text inert when it is rendered outside a code span."""
    sanitized = html.escape(_safe_ledger_text(value, limit=limit), quote=False)
    return re.sub(r"([\\`*_\[\]()#!~>])", r"\\\1", sanitized)


COMMAND_VALUE_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._:/+-]{0,199}\Z")


def _regeneration_argv(
    provider_name: str,
    region: str,
    model: str,
    judge_model: str,
) -> list[str] | None:
    values = (provider_name, region, model, judge_model)
    if any(
        not _is_utf8_encodable(value) or COMMAND_VALUE_RE.fullmatch(value) is None
        for value in values
    ):
        return None
    return [
        "python",
        "scripts/eval_run.py",
        "--provider",
        provider_name,
        "--region",
        region,
        "--model",
        model,
        "--judge-model",
        judge_model,
        "--ledger",
        "evals/eval-run-ledger.md",
    ]


def _powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _regeneration_command_lines(argv: list[str] | None) -> list[str]:
    if argv is None:
        return [
            "Regeneration commands omitted because CLI metadata contains unsafe shell or ",
            "Markdown characters; re-enter those values manually.",
        ]
    return [
        "Preview regeneration from a POSIX shell (offline):",
        "",
        "```sh",
        shlex.join(argv),
        "```",
        "",
        "Preview regeneration from PowerShell (offline):",
        "",
        "```powershell",
        "& " + " ".join(_powershell_quote(value) for value in argv),
        "```",
        "",
        "Review the plan, then add `--live --max-calls N` and an optional ",
        "`--max-output-tokens N` to execute. Replace N with your chosen positive ",
        "ceiling. Input-token charges and currency cost are not capped.",
    ]



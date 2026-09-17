from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence, TextIO


ESCAPE_RE = re.compile(r"\\|")


@dataclass(frozen=True)
class TableIssue:
    path: str
    line: int
    code: str
    message: str
    context: Optional[str] = None


@dataclass
class TableBlock:
    path: str
    start_line: int
    end_line: int
    header: List[str]
    align: List[Optional[str]]
    rows: List[List[str]]

    def header_line(self) -> str:
        return "|" + "|".join(self.header) + "|"

    def sep_line(self) -> str:
        cells = []
        for width, align in zip(_row_widths(self), self.align):
            marker = ":"
            if align == "left":
                marker = ":--"
            elif align == "right":
                marker = "--:"
            elif align == "center":
                marker = ":-:"
            cells.append(marker + "-" * (width - len(marker)))
        return "|" + "|".join(cells) + "|"


_TABLE_HEAD_RE = re.compile(r"^\s*\|.*\|\s*$")
_SEP_RE = re.compile(r"^\s*\|(?:\s*:?-+:?\s*\|)+\s*$")
_COL_SPLIT_RE = re.compile(r"(?<!\\)\|")


def _split_row(row: str) -> List[str]:
    parts = _COL_SPLIT_RE.split(row)
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return [cell.strip() for cell in parts]


def _parse_align(sep: str) -> List[Optional[str]]:
    parts = _split_row(sep)
    result: List[Optional[str]] = []
    for part in parts:
        left = part.startswith(":")
        right = part.endswith(":")
        if left and right:
            result.append("center")
        elif left:
            result.append("left")
        elif right:
            result.append("right")
        else:
            result.append(None)
    return result


def _parse_tables(path: str, text: str) -> List[TableBlock]:
    tables: List[TableBlock] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not _TABLE_HEAD_RE.match(line):
            i += 1
            continue

        start = i
        header = _split_row(line)
        if i + 1 >= len(lines):
            break
        sep_line = lines[i + 1]
        if not _SEP_RE.match(sep_line):
            i += 1
            continue

        align = _parse_align(sep_line)
        if len(align) != len(header):
            i += 1
            continue

        i += 2
        rows: List[List[str]] = []
        while i < len(lines) and _TABLE_HEAD_RE.match(lines[i]):
            row = _split_row(lines[i])
            rows.append(row)
            i += 1

        tables.append(
            TableBlock(
                path=path,
                start_line=start + 1,
                end_line=i,
                header=header,
                align=align,
                rows=rows,
            )
        )
    return tables


def _row_widths(table: TableBlock) -> List[int]:
    widths = [len(h) for h in table.header]
    for row in table.rows:
        for idx, cell in enumerate(row):
            if idx < len(widths):
                widths[idx] = max(widths[idx], len(cell))
    return widths


def _fmt_cell(value: str, width: int, align: Optional[str]) -> str:
    if align == "left":
        return value.ljust(width)
    if align == "right":
        return value.rjust(width)
    if align == "center":
        return value.center(width)
    return value.ljust(width)


def _format_table(table: TableBlock) -> str:
    widths = _row_widths(table)

    header_cells = [
        _fmt_cell(value, widths[idx], table.align[idx])
        for idx, value in enumerate(table.header)
    ]
    sep_cells = []
    for width, align in zip(widths, table.align):
        marker = ""
        if align == "left":
            marker = ":--"
        elif align == "right":
            marker = "--:"
        elif align == "center":
            marker = ":-:"
        sep_cells.append(marker + "-" * (width - len(marker)))

    body = [header_cells, sep_cells]
    for row in table.rows:
        body.append(
            [
                _fmt_cell(value, widths[idx], table.align[idx] if idx < len(table.align) else None)
                for idx, value in enumerate(row)
            ]
        )

    return "\n".join("|" + "|".join(cells) + "|" for cells in body)


def lint_table(table: TableBlock) -> List[TableIssue]:
    issues: List[TableIssue] = []
    expected_cols = len(table.header)
    widths = _row_widths(table)

    if any(len(h.strip()) == 0 for h in table.header):
        issues.append(
            TableIssue(
                path=table.path,
                line=table.start_line,
                code="MT001",
                message="Table header contains empty column(s).",
                context=table.header_line(),
            )
        )

    sep_line = table.sep_line()
    for idx, width in enumerate(widths):
        if width < 3:
            issues.append(
                TableIssue(
                    path=table.path,
                    line=table.start_line + 1,
                    code="MT002",
                    message=f"Column {idx + 1} is too narrow ({width} chars).",
                    context=sep_line,
                )
            )

    for row_idx, row in enumerate(table.rows):
        if len(row) != expected_cols:
            issues.append(
                TableIssue(
                    path=table.path,
                    line=table.start_line + 2 + row_idx,
                    code="MT004",
                    message=f"Row has {len(row)} columns; expected {expected_cols}.",
                    context="|".join(row),
                )
            )

    return issues


def lint_text(path: str, text: str) -> List[TableIssue]:
    issues: List[TableIssue] = []
    for table in _parse_tables(path, text):
        issues.extend(lint_table(table))
    return issues


def lint_path(path: str) -> List[TableIssue]:
    return lint_text(path, Path(path).read_text(encoding="utf-8"))


def format_text(path: str, text: str) -> str:
    tables = _parse_tables(path, text)
    if not tables:
        return text

    result: List[str] = []
    pos = 0
    for table in tables:
        result.append(text[pos : table.start_line - 1])
        result.append(_format_table(table))
        pos = table.end_line
    result.append(text[pos:])
    return "\n".join(result)


def format_path(path: str) -> str:
    return format_text(path, Path(path).read_text(encoding="utf-8"))


def _write_output(data: str, out: TextIO) -> None:
    out.write(data)
    if not data.endswith("\n"):
        out.write("\n")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mdtablefmt",
        description="Detect, format, and normalize markdown tables.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["-"],
        help="Markdown files or `-` for stdin.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only report issues; do not rewrite files.",
    )
    parser.add_argument("--format", choices=["plain", "markdown"], default="plain")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Rewrite formatted tables back to the original file.",
    )
    parser.add_argument(
        "--stdin-name",
        default="<stdin>",
        help="Logical path name for stdin input.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    issues: List[TableIssue] = []

    if len(args.paths) == 1 and args.paths[0] == "-":
        raw = sys.stdin.read()
        if not raw:
            return 0
        path = args.stdin_name
        issues.extend(lint_text(path, raw))
        if not args.check and not args.in_place:
            _write_output(format_text(path, raw), sys.stdout)
            return 0 if not issues else 1
        if args.in_place:
            Path(path).write_text(format_text(path, raw), encoding="utf-8")
    else:
        changed = False
        for raw_path in args.paths:
            text = Path(raw_path).read_text(encoding="utf-8")
            issues.extend(lint_text(raw_path, text))
            formatted = format_text(raw_path, text)
            if formatted != text:
                changed = True
                if args.in_place:
                    Path(raw_path).write_text(formatted, encoding="utf-8")

        if not args.check:
            if not args.in_place:
                for raw_path in args.paths:
                    text = Path(raw_path).read_text(encoding="utf-8")
                    _write_output(format_text(raw_path, text), sys.stdout)
            return 0 if not issues else 1

    if args.format == "plain":
        for issue in issues:
            print(f"{issue.path}:{issue.line}:{issue.code}: {issue.message}")
    else:
        for issue in issues:
            print(f"| {issue.path} | {issue.line} | {issue.code} | {issue.message} |")

    return 1 if issues else 0

from mdtablefmt import (
    TableBlock,
    lint_table,
    lint_path,
    format_text,
    main,
)


def test_lint_empty_header():
    table = TableBlock(
        path="x.md",
        start_line=1,
        end_line=3,
        header=["", "name"],
        align=[None, None],
        rows=[],
    )
    issues = lint_table(table)
    assert any(issue.code == "MT001" for issue in issues)


def test_lint_width():
    table = TableBlock(
        path="x.md",
        start_line=1,
        end_line=3,
        header=["a", "name"],
        align=[None, None],
        rows=[["1", "x"]],
    )
    issues = lint_table(table)
    assert any(issue.code == "MT002" for issue in issues)


def test_lint_row_column_mismatch():
    table = TableBlock(
        path="x.md",
        start_line=1,
        end_line=3,
        header=["id", "name"],
        align=[None, None],
        rows=[["1", "a", "b"]],
    )
    issues = lint_table(table)
    assert any(issue.code == "MT004" for issue in issues)


def test_format_preserves_alignment():
    text = "|id|name|\n|:--|--:|\n|10|alpha|\n|1|beta|\n"
    formatted = format_text("x.md", text)
    assert "|:--|" in formatted
    assert "--:|" in formatted


def test_lint_path_returns_issues(tmp_path):
    md = tmp_path / "sample.md"
    md.write_text("|id|name|\n|--|--|\n|1|\n", encoding="utf-8")
    issues = lint_path(str(md))
    assert issues
    assert any(issue.code == "MT004" for issue in issues)


def test_main_check_exits_nonzero(tmp_path):
    md = tmp_path / "sample.md"
    md.write_text("|id|name|\n|--|--|\n|1|\n", encoding="utf-8")
    assert main(["--check", str(md)]) == 1


def test_main_format_stdout(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin.read", lambda: "|id|name|\n|--|--|\n|1|alpha|\n")
    main(["-"])
    out = capsys.readouterr().out
    assert "|" in out

import csv
from pathlib import Path

import pytest

from scripts.import_sprint_issues import import_issues, load_rows, parse_labels


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_load_rows_accepts_valid_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "issues.csv"
    columns = ["story_id", "title", "body", "labels", "sprint"]
    row = {
        "story_id": "S1-001",
        "title": "Add feature",
        "body": "Details",
        "labels": "sprint-1",
        "sprint": "Sprint 1",
    }
    write_csv(csv_path, columns, [row])

    assert load_rows(csv_path) == [row]


def test_load_rows_rejects_missing_required_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "issues.csv"
    write_csv(csv_path, ["story_id", "title"], [])

    with pytest.raises(ValueError, match="body, labels, sprint"):
        load_rows(csv_path)


def test_load_rows_rejects_blank_title_before_import(tmp_path: Path) -> None:
    csv_path = tmp_path / "issues.csv"
    columns = ["story_id", "title", "body", "labels", "sprint"]
    row = {
        "story_id": "S1-002",
        "title": " ",
        "body": "Details",
        "labels": "",
        "sprint": "Sprint 1",
    }
    write_csv(csv_path, columns, [row])

    with pytest.raises(ValueError, match="S1-002 has no title"):
        load_rows(csv_path)


def test_parse_labels_trims_and_ignores_empty_labels() -> None:
    assert parse_labels(" sprint-1, , backend ") == ["sprint-1", "backend"]


def test_import_issues_skips_existing_titles_without_posting() -> None:
    rows = [
        {
            "story_id": "S1-001",
            "title": "Already exists",
            "body": "Details",
            "labels": "",
            "sprint": "Sprint 1",
        }
    ]
    calls = []

    def api_request(method: str, path: str, payload: dict | None = None) -> list | dict:
        calls.append((method, path, payload))
        if path.startswith("/repos/example/repository/issues?"):
            return [{"title": "Already exists"}]
        if path.startswith("/repos/example/repository/labels?"):
            return []
        raise AssertionError(f"Unexpected API request: {method} {path}")

    assert import_issues(rows, "example/repository", True, api_request) == (0, 1)
    assert len(calls) == 2

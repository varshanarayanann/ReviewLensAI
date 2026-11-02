import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

REQUIRED_COLUMNS = {"story_id", "title", "body", "labels", "sprint"}
ApiRequest = Callable[[str, str, dict[str, Any] | None], Any]


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.exists():
        raise ValueError(f"CSV file not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                "CSV is missing required column(s): " + ", ".join(sorted(missing))
            )

        rows = list(reader)

    for row in rows:
        if not row["title"].strip():
            story_id = row["story_id"].strip() or "Unknown story"
            raise ValueError(f"{story_id} has no title.")

    return rows


def parse_labels(value: str) -> list[str]:
    return [label.strip() for label in value.split(",") if label.strip()]


def make_api_request(
    token: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    url = f"https://api.github.com{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cs490-sprint-issue-importer",
        },
    )

    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API request failed: {method} {path} "
            f"returned HTTP {exc.code}: {details}"
        ) from exc


def get_all_issues(repository: str, api_request: ApiRequest) -> list[dict[str, Any]]:
    issues = []
    page = 1
    while True:
        query = urllib.parse.urlencode({"state": "all", "per_page": 100, "page": page})
        batch = api_request("GET", f"/repos/{repository}/issues?{query}", None)
        if not batch:
            break

        issues.extend(issue for issue in batch if "pull_request" not in issue)
        if len(batch) < 100:
            break
        page += 1

    return issues


def get_existing_labels(repository: str, api_request: ApiRequest) -> set[str]:
    labels = set()
    page = 1
    while True:
        query = urllib.parse.urlencode({"per_page": 100, "page": page})
        batch = api_request("GET", f"/repos/{repository}/labels?{query}", None)
        if not batch:
            break

        labels.update(label["name"] for label in batch)
        if len(batch) < 100:
            break
        page += 1

    return labels


def ensure_labels(
    repository: str,
    label_names: list[str],
    existing_labels: set[str],
    dry_run: bool,
    api_request: ApiRequest,
) -> None:
    for label in label_names:
        if label in existing_labels:
            continue

        if dry_run:
            print(f"[DRY RUN] Would create label: {label}")
        else:
            api_request(
                "POST",
                f"/repos/{repository}/labels",
                {"name": label, "color": "5319e7", "description": "Sprint issue label"},
            )
            print(f"Created label: {label}")

        existing_labels.add(label)


def import_issues(
    rows: list[dict[str, str]],
    repository: str,
    dry_run: bool,
    api_request: ApiRequest,
) -> tuple[int, int]:
    existing_issues = get_all_issues(repository, api_request)
    existing_titles = {issue["title"] for issue in existing_issues}
    existing_labels = get_existing_labels(repository, api_request)
    created = 0
    skipped = 0

    for row in rows:
        title = row["title"].strip()
        body = row["body"].strip()
        labels = parse_labels(row["labels"])

        if title in existing_titles:
            print(f"SKIP: Issue already exists: {title}")
            skipped += 1
            continue

        ensure_labels(repository, labels, existing_labels, dry_run, api_request)
        if dry_run:
            print(f"[DRY RUN] Would create: {title}")
        else:
            issue = api_request(
                "POST",
                f"/repos/{repository}/issues",
                {"title": title, "body": body, "labels": labels},
            )
            print(f"CREATED: #{issue['number']} {title}")

        existing_titles.add(title)
        created += 1

    return created, skipped


def main() -> int:
    try:
        token = os.environ["GITHUB_TOKEN"]
        repository = os.environ["GITHUB_REPOSITORY"]
        csv_path = Path(os.environ["CSV_PATH"])
        dry_run = os.environ["DRY_RUN"].lower() == "true"
    except KeyError as exc:
        print(
            f"ERROR: Missing required environment variable: {exc.args[0]}",
            file=sys.stderr,
        )
        return 1

    try:
        rows = load_rows(csv_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    def api_request(
        method: str, path: str, payload: dict[str, Any] | None = None
    ) -> Any:
        return make_api_request(token, method, path, payload)

    print(f"Repository: {repository}")
    print(f"CSV file: {csv_path}")
    print(f"Rows found: {len(rows)}")
    print(f"Dry run: {dry_run}")
    print()

    created, skipped = import_issues(rows, repository, dry_run, api_request)
    mode = "would be created" if dry_run else "created"
    print(f"\nImport complete: {created} issue(s) {mode}; {skipped} skipped.")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write("## Sprint Issue Import\n\n")
            summary.write(f"- CSV: `{csv_path}`\n")
            summary.write(f"- Rows: {len(rows)}\n")
            summary.write(f"- Issues {mode}: {created}\n")
            summary.write(f"- Existing issues skipped: {skipped}\n")
            summary.write(f"- Dry run: `{dry_run}`\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Development

The repository's current executable project code is the Python sprint-issue
importer. Use Python 3.12 or newer and run these commands from the repository
root.

Install the shared development tools:

```text
python -m pip install -r requirements-dev.txt
```

Check lint and imports:

```text
python -m ruff check .
```

Check formatting:

```text
python -m ruff format --check .
```

Run the automated tests (no browser or GitHub credentials required):

```text
python -m pytest
```

To apply the configured formatter, run `python -m ruff format .`. The GitHub
Actions issue-import workflow and local tooling both use
`scripts/import_sprint_issues.py`.

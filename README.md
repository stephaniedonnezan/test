# Linear issue title research prefix

This repository contains a small, side-effect-free handler for Cursor/Linear
automation payloads. When an issue status-change event moves to `to research`,
the handler returns an action to prefix the issue title with
`Cursor researching`.

## Behavior

- Matches status-change triggers such as `status_changed`, `statusChanged`, and
  generic issue update events whose changed fields include status/state.
- Normalizes status casing and separators, so `To Research`, `to_research`, and
  `toResearch` are treated the same.
- Skips issues whose titles already start with `Cursor researching`.
- Returns `None` for non-status triggers, non-target statuses, or missing issue
  identifiers/titles.

## Usage

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
if update:
    # Apply update["title"] to update["issueId"] using the Linear API.
    ...
```

The module can also be used as a CLI that reads a JSON payload from stdin and
prints the update action:

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```

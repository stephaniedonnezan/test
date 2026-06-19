# Linear issue title prefix automation

This repository contains a small, side-effect-free handler for Linear status
change automations.

When an issue status change moves to `to research`, `linear_title_prefix.py`
returns an action instructing the caller to update the issue title with:

```text
Cursor researching: <existing title>
```

The handler ignores unrelated triggers, statuses other than `to research`, and
titles that already start with `Cursor researching`.

## Usage

Pass the automation payload on standard input:

```bash
python3 linear_title_prefix.py < payload.json
```

When the payload should update an issue title, the script prints JSON like:

```json
{"action": "update_issue_title", "issueId": "POI-5001", "title": "Cursor researching: Timezone selector acts as filter"}
```

When no title update is needed, the script exits successfully without output.

## Tests

```bash
python3 -m unittest -v
```

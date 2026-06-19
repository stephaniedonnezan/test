# Linear issue-title prefix automation

This repository contains a small automation helper for Linear issue status
changes. When an issue moves to `to research`, the helper returns an action that
prefixes the issue title with `Cursor researching`.

```bash
python3 linear_title_prefix.py < event.json
```

For a matching event, the command prints:

```json
{"action": "update_issue_title", "issueId": "POI-4961", "title": "Cursor researching: Remove Subscribe button on invite"}
```

No output means the event should be ignored. The prefix is not duplicated when a
title already starts with `Cursor researching`.

Run the tests with:

```bash
python3 -m unittest -v
```

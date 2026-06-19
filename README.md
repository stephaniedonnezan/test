# Linear issue-title prefix automation

This repository contains a small automation helper for Linear issue status
changes. When an issue moves to `to research`, the helper returns an action that
prefixes the issue title with `Cursor researching`.

```bash
python3 linear_title_prefix.py < event.json
```

For a matching event, the command prints:

```json
{"action": "update_issue_title", "issueId": "POI-5018", "title": "Cursor researching: Error alert with repeating txt when entering high amount of proposed GO"}
```

No output means the event should be ignored. The prefix is not duplicated when a
title already starts with `Cursor researching`.

Run the tests with:

```bash
python3 -m unittest -v
```

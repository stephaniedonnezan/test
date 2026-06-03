# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automations.

When an issue status changes to `to research`, `linear_title_prefix.py` returns
an action that prefixes the issue title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4780",
  "title": "Cursor researching: Bug closing 2 deliveries"
}
```

The handler ignores other status changes and avoids adding the prefix when the
title already starts with `Cursor researching`.

## Run tests

```sh
python3 -m unittest -v
```

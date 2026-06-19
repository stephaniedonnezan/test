# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automations.

When an issue status changes to `To Research`, `build_issue_title_update` returns
an action payload that adds the `Cursor researching` prefix to the issue title:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4382",
  "title": "Cursor researching: Allow overrides in spreadsheets on test comparisons"
}
```

The handler ignores other statuses and avoids adding the prefix when the issue
title already starts with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

The CLI prints the update action for matching events and exits without output
for events that should not change the issue title.

## Tests

```bash
python3 -m unittest -v
```

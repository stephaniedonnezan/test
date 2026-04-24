# test

## Linear status-change title helper

`linear_issue_title.py` computes whether a Linear issue title should be updated
based on status-change webhook payloads.

Behavior:
- when a Linear `issue` webhook has `trigger=status_changed` and
  `newStatus=to research`, it returns a title prefixed with
  `Cursor researching: `
- otherwise it returns no update (`title: null`)

Run manually:

```bash
python3 linear_issue_title.py <<'JSON'
{
  "triggerContext": {
    "triggerType": "linear",
    "webhookType": "issue",
    "trigger": "status_changed",
    "newStatus": "to research",
    "title": "Dashboard: Selecting the current year breaks"
  }
}
JSON
```

Run tests:

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

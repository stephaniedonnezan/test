# Linear issue title prefix automation

Adds a `Cursor researching` prefix to Linear issue titles when an issue status
change moves the issue to `To Research`.

## Usage

Pass a Linear/Cursor automation event as JSON on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

When the event is a status-change transition to `To Research`, the script prints
an update action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4934",
  "title": "Cursor researching: Existing issue title"
}
```

For unrelated events, it prints `null`.

## Tests

```bash
python3 -m unittest -v
```

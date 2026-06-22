# Linear issue title automation

Adds a `Cursor researching` marker to Linear issue titles when an issue status
changes to `to research`.

## Usage

Pass the Linear automation event as JSON on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

For matching status changes, the command prints an update action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5097",
  "title": "Cursor researching: QA report POI-4578"
}
```

For other events, it prints `null`.

## Tests

```bash
python3 -m unittest -v
```

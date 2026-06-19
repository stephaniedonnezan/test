# Linear issue title automation

Adds `Cursor researching` to a Linear issue title when a status-change event moves
the issue to `to research`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

Matching events print an `update_issue_title` action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4666",
  "title": "Cursor researching: Fix the issue"
}
```

## Tests

```bash
python3 -m unittest -v
```

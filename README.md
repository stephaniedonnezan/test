# Linear title prefix automation

Adds `Cursor researching` to a Linear issue title when an issue status changes
to `to research`.

## Usage

Pass the automation payload as JSON on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

When the payload matches, the script prints an action object:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4014",
  "title": "Cursor researching: CSV generator maps reviewed ISCC JSON fields to a valid Nabisy 2025-08 export"
}
```

For non-matching payloads, it prints `null`.

## Tests

```bash
python3 -m unittest -v
```

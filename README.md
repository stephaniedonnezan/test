# Linear issue title prefix automation

Adds the `Cursor researching` prefix to Linear issue titles when an issue status
changes to `to research`.

The handler returns a transport-agnostic action for the caller to apply:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3628",
  "title": "Cursor researching: Update Transport Event to have TransportEventLocationEntity"
}
```

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```

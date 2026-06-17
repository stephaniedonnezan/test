# Linear issue title prefix automation

Adds a `Cursor researching` prefix to Linear issue titles when a status-change
event moves the issue to `To Research`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

For a matching event, the command prints an action payload:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3860",
  "title": "Cursor researching: Meter table should display sites"
}
```

Non-matching events print `null`.

## Tests

```bash
python3 -m unittest -v
```

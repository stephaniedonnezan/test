# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when a status-change event moves
the issue to `to research`.

## Usage

Pipe a Linear/Cursor automation payload into the handler:

```bash
python3 linear_title_prefix.py < payload.json
```

When the event qualifies, the script prints an action object:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4751",
  "title": "Cursor researching: Existing issue title"
}
```

For non-matching events, missing issue data, or titles that already start with
`Cursor researching`, the script prints `null`.

## Tests

```bash
python3 -m unittest -v
```

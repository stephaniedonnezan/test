# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when a status-change trigger
moves the issue to `to research`.

## Usage

Pipe the Linear/Cursor automation payload into the handler:

```bash
python3 linear_title_prefix.py < payload.json
```

When the event qualifies, the command prints an update action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4693",
  "title": "Cursor researching: Existing issue title"
}
```

Events that are not status changes, do not move to `to research`, or already
start with `Cursor researching` produce no output.

## Tests

```bash
python3 -m unittest -v
```

# Linear issue title automation

Adds `Cursor researching` to a Linear issue title when the issue status changes
to `to research`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

For matching events, the command prints an `update_issue_title` action:

```json
{"action": "update_issue_title", "issueId": "POI-4975", "title": "Cursor researching: Example issue"}
```

Events that are not status changes to `to research`, or titles that already
start with `Cursor researching`, produce no output.

## Tests

```bash
python3 -m unittest -v
```

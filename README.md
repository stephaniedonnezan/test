# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when an issue status changes
to `To Research`.

## Usage

Pass a Linear/Cursor automation event as JSON on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

The script prints an `update_issue_title` action when the title should be
changed, or `null` when the event does not match.

## Tests

```bash
python3 -m unittest -v
```

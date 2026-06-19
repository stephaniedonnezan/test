# Linear title prefix automation

Adds a `Cursor researching` prefix to Linear issue titles when a status-change
event moves an issue to `To Research`.

The handler is side-effect free. `build_issue_title_update(event)` returns an
action for callers to execute with their Linear client:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4598",
  "title": "Cursor researching: Make every mb use the same component"
}
```

It accepts flat Cursor automation payloads as well as nested Linear issue update
payloads, normalizes status casing/separators, and skips titles that already
start with `Cursor researching`.

## Usage

```sh
python3 linear_title_prefix.py < event.json
```

No output is printed when no title update is needed.

## Tests

```sh
python3 -m unittest -v
```

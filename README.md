# Linear issue title prefix automation

Adds a small handler for Linear issue status-change events. When an issue moves
to `to research`, `build_issue_title_update` returns an action that prefixes the
issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The handler returns `None` for unrelated events, non-research statuses, missing
issue data, or titles that already begin with `Cursor researching`.

## CLI

The module can also read a JSON event from standard input:

```bash
python3 linear_title_prefix.py < event.json
```

When an update is needed it prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4637",
  "title": "Cursor researching: Remove obsolete emissions inputs"
}
```

## Tests

```bash
python3 -m unittest -v
```

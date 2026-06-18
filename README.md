# Linear research title prefix automation

Adds an idempotent `Cursor researching` title prefix when a Linear issue status
changes to `to research`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

For matching events, the script prints an action object:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-2598",
  "title": "Cursor researching: Site management deliveries table"
}
```

The handler is also importable:

```python
from linear_title_prefix import build_issue_title_update
```

## Tests

```bash
python3 -m unittest -v
```

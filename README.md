# Linear issue title automation

Adds a `Cursor researching` prefix to a Linear issue title when a status-change
event moves the issue to `To Research`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The function returns an action shaped like this when a title update is needed:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5036",
  "title": "Cursor researching: Mass Balance canvas items in delivery opacity off"
}
```

It returns `None` for unrelated triggers, statuses other than `To Research`, or
titles that already start with `Cursor researching`.

## Testing

```bash
python3 -m unittest -v
```

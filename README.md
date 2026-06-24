# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when the issue status changes
to `to research`.

## Usage

The handler exposes `build_issue_title_update(event)`, which returns an update
action when the payload matches the research-status transition:

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

It can also read a JSON event from stdin:

```bash
python3 linear_title_prefix.py < event.json
```

Matching events produce:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4578",
  "title": "Cursor researching: Existing issue title"
}
```

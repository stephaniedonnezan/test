# Linear issue title prefix automation

Adds a `Cursor researching` marker to Linear issue titles when an issue status
change moves the issue to `to research`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For matching events, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4579",
  "title": "Cursor researching: MB export corrections"
}
```

Non-matching events return `None`. The module can also be run as a CLI that
reads a JSON event from stdin and prints the update action when one is needed:

```bash
python3 linear_title_prefix.py < event.json
```

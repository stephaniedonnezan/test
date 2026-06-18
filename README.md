# Linear issue title prefix automation

Adds a `Cursor researching` prefix to Linear issue titles when an issue status
changes to `to research`.

The automation helper is exposed by `linear_title_prefix.py`:

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For matching status-change payloads, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4871",
  "title": "Cursor researching: Existing issue title"
}
```

Non-matching events return `None`. The CLI also accepts a JSON payload on stdin
and prints the action or `null`.

Run tests with:

```sh
python3 -m unittest -v
```

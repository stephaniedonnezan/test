# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when an issue status changes
to `To Research`.

The handler is side-effect free: it returns the issue update action for the
automation runtime to execute.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

Matching events return:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4902",
  "title": "Cursor researching: Assert timeline consistency before delivery issuance"
}
```

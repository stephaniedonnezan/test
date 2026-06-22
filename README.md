# Linear title prefix automation

Adds `Cursor researching` to a Linear issue title when the issue status changes to
`to research`.

## Usage

Pass a Linear/Cursor automation payload to `build_issue_title_update`:

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

When the event is a matching status change, the helper returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5059",
  "title": "Cursor researching: Existing issue title"
}
```

For non-matching events, missing issue data, or titles that already start with
`Cursor researching`, it returns `None`.

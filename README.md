# Linear issue title prefix automation

Adds a `Cursor researching` prefix to Linear issue titles when an issue status
changes to `to research`.

## Usage

Pass a Linear webhook or Cursor automation trigger payload as JSON on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

When the payload represents a matching status change, the script prints an
update action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4047",
  "title": "Cursor researching: Existing title"
}
```

# Linear title prefix automation

Adds a `Cursor researching` prefix to Linear issue titles when an issue status
change moves the issue into `to research`.

The handler accepts a Linear/Cursor event payload and returns an
`update_issue_title` action when the title should be changed:

```bash
python3 linear_title_prefix.py < event.json
```

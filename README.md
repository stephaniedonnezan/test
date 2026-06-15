# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when an issue status changes
to `to research`.

The handler is side-effect free: `build_issue_title_update(event)` returns an
`update_issue_title` action for the caller to apply through the Linear API, or
`None` when no title update is needed.

Run tests with:

```bash
python3 -m unittest -v
```

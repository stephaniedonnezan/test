# Linear issue title automation

Adds a `Cursor researching` prefix to Linear issue titles when an issue status
changes to `to research`.

The handler exposes `build_issue_title_update(event)`, which returns an
`update_issue_title` action for matching status-change events and `None` for
all other payloads.

Run the tests with:

```bash
python3 -m unittest -v
```

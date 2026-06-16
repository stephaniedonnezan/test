# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when an issue status changes to
`to research`.

The main entrypoint is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an `update_issue_title` action for matching
status-change payloads and `None` for events that should be ignored.

Run tests with:

```bash
python3 -m unittest -v
```

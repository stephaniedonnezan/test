# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automation events.

When an issue status changes to `to research`, `build_issue_title_update(event)`
returns an update action that prefixes the title with `Cursor researching`.
Events for other statuses, non-status triggers, missing issue metadata, or titles
that already start with the prefix are ignored.

Run the tests with:

```bash
python3 -m unittest -v
```

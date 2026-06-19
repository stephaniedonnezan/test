# Linear research title prefix

This repository contains a small handler for Linear status-change events.

When an issue moves to `to research`, `build_issue_title_update` returns an
`update_issue_title` action with the title prefixed by `Cursor researching`.
Events for other statuses, non-status changes, or titles that already contain
the prefix are ignored.

Run the unit tests with:

```bash
python3 -m unittest -v
```

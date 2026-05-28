# Linear research title prefix

This repository contains a small handler for Linear issue status-change
automations.

`build_issue_title_update(event)` returns an `update_issue_title` action when an
issue status changes to `to research`. The returned title is prefixed with
`Cursor researching` unless the title already starts with that text.

Run tests with:

```bash
python3 -m unittest -v
```

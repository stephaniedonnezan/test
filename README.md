# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automation.

`build_issue_title_update(event)` returns an `update_issue_title` action only when a Linear issue status changes to `To Research`. The returned title is prefixed with `Cursor researching: `, and already-prefixed titles are ignored so the prefix is not duplicated.

Run the tests with:

```bash
python3 -m unittest -v
```

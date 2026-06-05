# Linear issue title automation

This repository contains a small handler for Linear status-change automation
payloads.

`build_issue_title_update(event)` returns an `update_issue_title` action when an
issue status changes to `To Research`, prefixing the issue title with
`Cursor researching:`. It returns `None` for unrelated events, non-research
statuses, missing issue data, or titles that already start with the prefix.

The module can also be used as a stdin JSON CLI:

```bash
python3 linear_title_prefix.py < payload.json
```

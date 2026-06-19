# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automations.

When a Linear issue status changes to `To Research`, `linear_title_prefix.py`
builds an `update_issue_title` action that prefixes the issue title with
`Cursor researching:`. Non-status changes, other statuses, and titles that
already start with `Cursor researching` are ignored.

The handler accepts flat Cursor `triggerContext` payloads, Cloud automation
payloads that wrap `triggerContext` under `automation_trigger_info`, and nested
Linear issue webhook payloads.

Run tests with:

```bash
python3 -m unittest -v
```

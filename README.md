# test

## Linear automation: research status title update

Use `linear_issue_title_updater.py` to update issue titles when a Linear issue
status changes to **to research**.

Behavior:
- Trigger must be `status_changed`
- `newStatus` (or `status`/`statusType`) must equal `to research`
- Title is prefixed once with `Cursor researching - `

Inputs:
- `AUTOMATION_TRIGGER_INFO` (JSON payload), or
- stdin JSON payload, or
- `--payload-file <path>`

Required environment variable for live updates:
- `LINEAR_API_KEY`

Quick local check:

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

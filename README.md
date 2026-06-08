# Linear research title automation

This repository contains a small Cursor/Linear automation helper.

## Cursor researching title prefix

Run `scripts/linear_research_title.py` from a Linear issue status-change automation. When the issue's new status is `to research`, the script prefixes the issue title with:

```text
Cursor researching:
```

The script is idempotent: if the title already contains `Cursor researching`, it does not update the title again.

### Configuration

Set `LINEAR_API_KEY` to a Linear API key with permission to update issues. The script reads the trigger payload from one of:

- `--payload-file path/to/payload.json`
- stdin
- `AUTOMATION_TRIGGER_INFO`
- `CURSOR_AUTOMATION_TRIGGER_INFO`
- `LINEAR_WEBHOOK_PAYLOAD`

Use `--dry-run` to print the update without calling Linear.

### Tests

```bash
python -m unittest discover -s tests
```

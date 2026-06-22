# Linear issue title automation

Adds `Cursor researching` to a Linear issue title when an issue status changes
to `to research`.

Run the helper against a Linear automation payload:

```bash
python3 linear_issue_title.py --payload-file payload.json
```

If `--payload-file` is omitted, the helper reads JSON from stdin.

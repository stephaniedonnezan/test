# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when the issue status changes
to `to research`.

The Python entrypoint is `linear_title_prefix.py`. It reads a JSON event from
stdin and prints an `update_issue_title` action when the title should be
updated:

```bash
python3 linear_title_prefix.py < event.json
```

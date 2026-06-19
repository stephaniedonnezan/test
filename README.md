# test

## Linear research title helper

`linear_issue_title.py` adds `Cursor researching` to a Linear issue title when
an issue status-change event moves to `to research`.

Example:

```bash
python3 linear_issue_title.py < trigger-context.json
```

For matching Linear issue status changes, the script prints a JSON payload with
the issue id and updated title. Non-matching events produce no output.

# Linear issue title prefix automation

Builds a Linear issue-title update when a status-change webhook moves an issue
to `to research`.

```bash
python3 linear_title_prefix.py < payload.json
```

For matching events, the script prints an `update_issue_title` action containing
the title prefixed with `Cursor researching`. For non-matching events, it prints
`null`.

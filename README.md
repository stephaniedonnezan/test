# Linear issue title automation

Builds an `update_issue_title` action when a Linear issue status changes to
`to research`. The action prefixes the issue title with `Cursor researching`
unless the title already starts with that prefix.

```bash
python3 linear_title_prefix.py < event.json
```

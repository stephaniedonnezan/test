# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automation events.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action payload that prefixes the issue title with
`Cursor researching`. Non-matching events return `None`.

Run the tests with:

```bash
python3 -m unittest -v
```

# Linear issue title prefix automation

Adds a `Cursor researching` title prefix when a Linear issue status-change
event moves the issue to `to research`.

The handler reads a JSON event from stdin and prints an `update_issue_title`
action when the title should be changed:

```sh
python3 linear_title_prefix.py < event.json
```

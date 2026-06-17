# Linear research title prefix automation

Adds `Cursor researching` to a Linear issue title when an issue status changes
to `to research`.

## Usage

Pass a Linear/Cursor automation event as JSON on stdin:

```sh
python3 linear_title_prefix.py < event.json
```

For matching status-change events, the script prints an `update_issue_title`
action containing the issue id and updated title. Non-matching events produce no
output.

## Tests

```sh
python3 -m unittest -v
```

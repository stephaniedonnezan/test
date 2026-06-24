# Linear research title prefix

This repository contains a small dependency-free handler for Linear issue status
change automations.

When a Linear issue status changes to `to research`, `linear_title_prefix.py`
builds an `update_issue_title` action that prefixes the issue title with
`Cursor researching`. Non-status changes, other statuses, and titles that
already start with the prefix are ignored.

Run the tests with:

```sh
python3 -m unittest -v
```

The module can also be used as a stdin/stdout JSON CLI:

```sh
python3 linear_title_prefix.py < event.json
```

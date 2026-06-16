# Linear issue title prefix helper

This repository contains a small Python helper for Linear status-change automations.

`linear_title_prefix.py` reads a Linear issue event and returns an `update_issue_title`
action when the issue status changes to `to research`. The new title is prefixed
with `Cursor researching: `, and already-prefixed titles are ignored.

Run the tests with:

```sh
python3 -m unittest -v
```

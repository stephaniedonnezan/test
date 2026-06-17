# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.

`linear_title_prefix.py` exposes `build_issue_title_update(event)`, which returns
an `update_issue_title` action when an issue status changes to `to research`.
The generated title is prefixed with `Cursor researching` unless that prefix is
already present.

When used as a CLI, the script reads a JSON payload from stdin and prints the
update action as JSON. Non-matching events produce no output.

Run the tests with:

```bash
python3 -m unittest -v
```

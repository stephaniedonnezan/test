# Linear issue title prefix automation

This repository contains a small, dependency-free handler for Cursor/Linear
status-change automations.

When an issue status changes to `to research`, `linear_title_prefix.py` builds
an `update_issue_title` action that prefixes the issue title with
`Cursor researching`. Existing titles that already start with that phrase are
left unchanged.

Run the test suite with:

```bash
python3 -m unittest -v
```

The module can also be used as a CLI by piping JSON on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

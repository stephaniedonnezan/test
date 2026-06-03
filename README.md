# Linear issue title prefix automation

Adds a `Cursor researching` prefix to Linear issue titles when a status-change
event moves an issue to `To Research`.

The `linear_title_prefix.py` module exposes `build_issue_title_update(payload)`,
which returns an `update_issue_title` action for callers to apply.

Run tests with:

```sh
python3 -m unittest -v
```

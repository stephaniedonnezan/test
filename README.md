# Linear research title prefix automation

Adds `Cursor researching` to a Linear issue title when a status-change event
moves the issue to `to research`.

The handler is exposed as `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an `update_issue_title` action when the
incoming payload matches the rule, otherwise it returns `None`.

Run tests with:

```sh
python3 -m unittest -v
```

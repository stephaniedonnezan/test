# test

## Linear research title prefix automation

`linear_title_prefix.py` builds an `update_issue_title` action when a Linear issue
status-change payload moves to `to research`. The generated title is prefixed
with `Cursor researching` unless that prefix is already present.

Run the unit tests with:

```sh
python3 -m unittest -v
```

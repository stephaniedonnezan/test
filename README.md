# Linear issue title prefix automation

Builds an `update_issue_title` action for Linear issue status-change events when
an issue moves to `to research`. The new title is prefixed with
`Cursor researching` unless it already has that prefix.

Run tests with:

```sh
python3 -m unittest -v
```

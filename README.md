# Linear title prefix automation

Builds an `update_issue_title` action when a Linear issue status-change event
moves an issue to `to research`. The generated title is prefixed with
`Cursor researching` unless it already has that prefix.

Run tests with:

```sh
python3 -m unittest -v
```

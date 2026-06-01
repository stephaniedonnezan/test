# Linear title prefix automation

Adds a `Cursor researching` title prefix when a Linear issue status changes to
`to research`.

The implementation is intentionally pure: `build_issue_title_update(event)`
returns an `update_issue_title` action for matching events and `None` otherwise.

Run the tests with:

```sh
python3 -m unittest -v
```

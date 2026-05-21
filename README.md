# Linear issue title automation

Adds the `Cursor researching` title prefix when a Linear issue status changes to
`to research`.

The main entrypoint is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an `update_issue_title` action for matching
events and `None` for events that should be ignored.

Run tests with:

```sh
python3 -m unittest -v
```

# Linear issue title automation

Adds a `Cursor researching` prefix to a Linear issue title when the issue status
changes to `To Research`.

The automation entry point is `build_issue_title_update` in
`linear_title_prefix.py`. It accepts the Linear trigger payload and returns an
`update_issue_title` action when the title should be changed.

Run tests with:

```sh
python3 -m unittest -v
```

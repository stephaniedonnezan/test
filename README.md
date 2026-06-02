# Linear title prefix automation

Adds a `Cursor researching` prefix to a Linear issue title when an issue status
changes to `to research`.

The automation entrypoint is `linear_title_prefix.py`. It reads a Linear event
payload from stdin and prints an `update_issue_title` action when a title update
is needed:

```sh
python3 linear_title_prefix.py < payload.json
```

Run tests with:

```sh
python3 -m unittest -v
```

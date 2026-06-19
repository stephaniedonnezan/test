# Linear issue title prefix automation

Builds an issue-title update action when a Linear issue status changes to
`to research`, prefixing the title with `Cursor researching`.

## Usage

Pass a Linear/Cursor automation JSON payload on stdin:

```sh
python3 linear_title_prefix.py < payload.json
```

Run tests with:

```sh
python3 -m unittest -v
```

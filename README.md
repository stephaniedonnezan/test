# Linear issue title prefix automation

Adds a `Cursor researching` prefix to Linear issue titles when an issue status
change moves the issue to `to research`.

The Python entrypoint is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an action payload like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4808",
  "title": "Cursor researching: Container events - unloading event error"
}
```

For non-matching events it returns `null` from the CLI, or `None` from Python.

## CLI

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```

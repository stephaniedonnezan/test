# Linear issue title prefix automation

Builds a Linear issue title update when an issue status changes to
`To Research`.

The handler exposes `build_issue_title_update(event)`, which returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-123",
  "title": "Cursor researching: Existing issue title"
}
```

For non-matching events it returns `null`/`None`.

## CLI

```sh
python3 linear_title_prefix.py < payload.json
```

## Tests

```sh
python3 -m unittest -v
```

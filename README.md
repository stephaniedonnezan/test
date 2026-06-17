# Linear issue title prefix automation

Adds a `Cursor researching` marker to a Linear issue title when an issue status
change moves it to `to research`.

## Usage

The automation entry point is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an update action for matching events:

```python
{
    "action": "update_issue_title",
    "issueId": "POI-4974",
    "title": "Cursor researching: User removal flow",
}
```

For non-matching events, missing issue metadata, or titles that already start
with `Cursor researching`, it returns `None`.

The module can also be used as a small CLI by piping a JSON payload on stdin:

```sh
python3 linear_title_prefix.py < event.json
```

## Verification

```sh
python3 -m unittest -v
```

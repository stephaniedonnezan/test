# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change automation payloads.

When an issue status changes to `to research`, `build_issue_title_update(event)` returns an
action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4139",
  "title": "Cursor researching: Error: can not calculate average on an empty array"
}
```

The handler returns `None` when no title update is needed, including non-status-change events,
other target statuses, missing issue data, or titles that already start with the prefix.

Run the tests with:

```sh
python3 -m unittest -v
```

The module can also be used as a CLI by piping a JSON event to stdin:

```sh
python3 linear_title_prefix.py < event.json
```

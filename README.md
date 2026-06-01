# Linear research title automation

This repository contains a small handler for Cursor/Linear automations that
prefixes an issue title with `Cursor researching` when the issue status changes
to `to research`.

The main entry point is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an action payload when a title update is
needed:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4144",
  "title": "Cursor researching: Front end improvements"
}
```

For non-matching events, or titles that already begin with `Cursor researching`,
the handler returns `None`.

## Testing

```sh
python3 -m unittest -v
```

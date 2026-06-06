# Linear research title prefix

This repository contains a small handler for Cursor/Linear automations. When a
Linear issue status-change event moves an issue to `To Research`, the handler
emits an `update_issue_title` action that prefixes the issue title with
`Cursor researching:`.

The handler ignores non-status updates, statuses other than `To Research`, and
titles that already start with `Cursor researching` to avoid duplicate prefixes.

## CLI usage

Pass the Linear webhook payload as JSON on standard input:

```sh
python3 linear_title_prefix.py < payload.json
```

For matching events, the command prints JSON like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4839",
  "title": "Cursor researching: UBA POS: version number is not incremented when there is an intermediate"
}
```

For non-matching events, the command exits with status `1` and prints nothing.

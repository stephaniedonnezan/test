# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automations.

When a Linear issue moves to `To Research`, `build_issue_title_update` returns a
transport-agnostic action asking the caller to prefix the issue title with
`Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-2809",
  "title": "Cursor researching: [625]Create new site entity"
}
```

The handler returns `null` for unrelated status changes, non-status triggers,
missing issue data, or titles that already start with `Cursor researching`.

## Usage

Pipe the automation event JSON into the module:

```sh
python3 linear_title_prefix.py < event.json
```

## Tests

```sh
python3 -m unittest -v
```

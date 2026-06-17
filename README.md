# Linear research status title prefix

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status changes to `To Research`, the handler returns a title update
that prefixes the issue title with `Cursor researching`.

## Usage

Pass the automation payload as JSON on stdin:

```sh
python3 linear_title_prefix.py < payload.json
```

For matching status-change events, the script prints an action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4899",
  "title": "Cursor researching: If the trading site is based in Germany or Spain"
}
```

Non-matching events print nothing.

## Tests

```sh
python3 -m unittest -v
```

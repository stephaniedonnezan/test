# Linear issue title prefix automation

This repository contains a small helper for Linear status-change automations.
When an issue status changes to `to research`, `linear_title_prefix.py` builds an
action that prefixes the issue title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5072",
  "title": "Cursor researching: Add first updated manual to codebase"
}
```

The helper is intentionally side-effect free. It accepts Cursor's flattened
`triggerContext` payloads and common nested Linear issue webhook payloads, then
returns `None` when no title change should be made.

## Development

Run the tests with:

```sh
python3 -m unittest -v
```

You can also pipe a JSON event to the CLI:

```sh
printf '%s\n' '{"trigger":"status_changed","newStatus":"To Research","id":"POI-5072","title":"Add first updated manual to codebase"}' \
  | python3 linear_title_prefix.py
```

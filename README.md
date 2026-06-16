# Linear issue title prefix

This repository contains a small helper for Linear issue status-change
automations. When an issue's status changes to `to research`, the helper builds
an action to prefix the issue title with `Cursor researching`.

## Behavior

`build_issue_title_update(event)` returns an update action like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4877",
  "title": "Cursor researching: Rounding error in power allocation"
}
```

The helper:

- accepts Cursor automation trigger payloads and common Linear issue webhook
  payloads;
- normalizes status and trigger casing/separators, including
  `status_changed`, `statusChanged`, `to_research`, and `To Research`;
- only acts on status-change events whose new status is `to research`;
- skips issues whose title already starts with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```

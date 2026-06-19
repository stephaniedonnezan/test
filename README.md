# Linear issue title prefix automation

This repository contains a small helper for Linear status-change automations.
When an issue is moved to **To Research**, `build_issue_title_update` returns an
action payload that prefixes the issue title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4966",
  "title": "Cursor researching: Invite landing page"
}
```

The helper accepts both Cursor's flat `triggerContext` payloads and nested
Linear issue webhook payloads. It ignores unrelated status changes and avoids
adding the prefix when a title already starts with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```

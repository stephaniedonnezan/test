# Linear issue title prefix automation

This repository contains a small helper for Cursor automations that react to
Linear issue status changes.

When an issue status changes to `To Research`, `linear_title_prefix.py` builds an
issue-title update action that prefixes the current title with:

```text
Cursor researching:
```

Already-prefixed titles are ignored so repeated webhook deliveries do not add
duplicate prefixes.

## Usage

Pass a Linear webhook payload or Cursor `triggerContext` JSON object on stdin:

```bash
python3 linear_title_prefix.py <<'JSON'
{
  "trigger": "status_changed",
  "newStatus": "To Research",
  "id": "POI-5031",
  "title": "Improve performance of timeZoneObject()"
}
JSON
```

Output:

```json
{"action": "update_issue_title", "issueId": "POI-5031", "title": "Cursor researching: Improve performance of timeZoneObject()"}
```

Payloads for other statuses, non-status changes, missing issue identifiers or
titles, and titles that already start with `Cursor researching` produce no
update.

## Tests

```bash
python3 -m unittest -v
```

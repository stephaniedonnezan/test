# Linear issue title prefix automation

This repository contains a small helper for Linear/Cursor automation payloads.
When an issue status changes to `To Research`, `linear_title_prefix.py` returns
an action that prefixes the issue title with `Cursor researching`.

```bash
echo '{"trigger":"status_changed","newStatus":"To Research","id":"POI-5033","title":"CO2 inputs optional proof file"}' \
  | python3 linear_title_prefix.py
```

Output:

```json
{"action": "update_issue_title", "issueId": "POI-5033", "title": "Cursor researching: CO2 inputs optional proof file"}
```

If the payload is not a status-change event, the new status is not `To Research`,
or the title already starts with `Cursor researching`, the helper avoids creating
an unnecessary duplicate title update.

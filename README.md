# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automation.

When an issue status changes to `to research`, `build_issue_title_update(event)`
returns an action payload that prefixes the issue title with
`Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5050",
  "title": "Cursor researching: Bug: compliant co2 mixed e_ex_use"
}
```

The handler accepts flat Cursor `triggerContext` payloads and nested Linear issue
update payloads. It ignores non-status-change events, ignores statuses other than
`to research`, and does not duplicate the prefix when it is already present.

You can also invoke the handler as a CLI that reads JSON from stdin:

```sh
python3 linear_title_prefix.py < event.json
```

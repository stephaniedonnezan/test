# Linear issue title prefix automation

This repository contains a small, side-effect-free handler for Cursor/Linear
automation payloads. When an issue status changes to `to research`, the handler
returns an action asking the caller to prefix the issue title with
`Cursor researching`.

The handler accepts both Cursor's flat `triggerContext` payloads and common
nested Linear webhook payloads.

## Usage

Pass the JSON webhook payload on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

For a matching status-change event, the script prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5037",
  "title": "Cursor researching: Able to delete supply contracts with connected meter readings"
}
```

Non-matching events print `null`.

## Tests

Run the unit tests with:

```bash
python3 -m unittest -v
```

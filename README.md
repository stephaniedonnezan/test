# Linear issue research title prefix

This repository contains a small handler for Linear status-change automation.

When an issue status changes to `To Research`, `linear_title_prefix.py` builds an
`update_issue_title` action that prefixes the title with `Cursor researching:`.
Events for other status changes, non-status triggers, and titles that already
begin with `Cursor researching` are ignored.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

For matching events, the CLI prints JSON like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5033",
  "title": "Cursor researching: CO2 inputs optional proof file"
}
```

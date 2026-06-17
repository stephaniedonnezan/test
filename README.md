# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automations. When an issue enters the `to research` status, the handler returns
an action that prefixes the issue title with `Cursor researching`.

```bash
python3 linear_title_prefix.py < event.json
```

For matching events, the command prints JSON like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4993",
  "title": "Cursor researching: Should the site card contain the button to site settings ?"
}
```

Events that are not status changes to `to research`, or titles already starting
with `Cursor researching`, do not produce an action.

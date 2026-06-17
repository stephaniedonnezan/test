# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automations.

When an issue status changes to `to research`, the handler returns an action to
prefix the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5021",
  "title": "Cursor researching: Add hydrogen input does not change anything in mass balance"
}
```

The handler ignores non-status-change events, statuses other than `to research`,
and titles that already start with `Cursor researching`.

## Usage

Run the handler with a Linear/Cursor automation payload on standard input:

```bash
python3 linear_title_prefix.py < payload.json
```

Run tests with:

```bash
python3 -m unittest -v
```

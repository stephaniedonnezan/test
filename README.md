# Linear research title automation

This repository contains a small, side-effect-free helper for Cursor/Linear
automations. When a Linear issue status-change event moves an issue to
`To Research`, `linear_title_prefix.py` builds an action that prefixes the issue
title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4788",
  "title": "Cursor researching: Prevent inconsistent timelines for customer events at ingestion time"
}
```

The helper ignores non-status-change events, status changes to other states, and
titles that already start with `Cursor researching`.

## Usage

Pass a Linear/Cursor event as JSON on standard input:

```sh
python3 linear_title_prefix.py < event.json
```

Run the tests with:

```sh
python3 -m unittest -v
```

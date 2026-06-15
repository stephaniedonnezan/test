# Linear issue title prefix automation

This repository contains a small, side-effect-free handler for Cursor/Linear
automation payloads.

When a Linear issue status changes to `to research`, `linear_title_prefix.py`
returns an action that prefixes the issue title with `Cursor researching`.
Other statuses, non-status events, missing issue data, and already-prefixed
titles return `null`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

The handler prints either:

```json
{"action": "update_issue_title", "issueId": "POI-3943", "title": "Cursor researching: Original title"}
```

or `null` when no title update should be applied.

## Tests

```bash
python3 -m unittest -v
```

# Linear issue title prefix helper

This repository contains a small, side-effect-free helper for Cursor/Linear
automations.

When a Linear issue status changes to `to research`, `linear_title_prefix.py`
builds an issue-title update action that prefixes the title with
`Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4934",
  "title": "Cursor researching: Issues panel must be visible across all tabs"
}
```

The helper accepts flat Cursor automation trigger payloads and common nested
Linear webhook shapes. Non-status events, status changes to other states, and
titles that already start with `Cursor researching` return `null`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```

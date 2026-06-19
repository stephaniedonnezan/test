# Linear issue title prefix helper

This repository contains a small, testable helper for Cursor/Linear automation
payloads.

When a Linear issue status changes to `to research`, `linear_title_prefix.py`
builds an action that prefixes the issue title with:

```text
Cursor researching
```

The helper returns `None` for unrelated status changes, non-status events,
missing issue data, or titles that already start with the prefix.

## Usage

Pass a JSON event payload on standard input:

```bash
python3 linear_title_prefix.py < event.json
```

Matching payloads print an action like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4935",
  "title": "Cursor researching: Issues indicator is mispositioned in container logic view"
}
```

Non-matching payloads print `null`.

## Tests

```bash
python3 -m unittest -v
```

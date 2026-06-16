# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automation events.
When an issue status change moves to `to research`, it builds the Linear title
update needed to add the `Cursor researching` marker:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4930",
  "title": "Cursor researching: Optimize offtaker fifo allocation"
}
```

The helper accepts flat Cursor automation trigger payloads and nested
Linear-style issue update payloads. It ignores unrelated status changes and
issues whose title already begins with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

Run tests with:

```bash
python3 -m unittest -v
```

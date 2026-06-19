# Linear title prefix helper

This repository contains a small, dependency-free helper for Cursor Automation
payloads triggered by Linear issue status changes.

When an issue moves to `To Research`, `linear_title_prefix.py` returns a JSON
action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5039",
  "title": "Cursor researching: Hide default emissions section"
}
```

The helper is idempotent: if the title already starts with `Cursor researching`,
no update action is returned.

## Usage

Pipe a Cursor/Linear webhook payload to the module:

```bash
python3 linear_title_prefix.py < payload.json
```

Run tests with:

```bash
python3 -m unittest -v
```

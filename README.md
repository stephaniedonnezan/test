# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automations. When an issue moves to `to research`, it returns an action that can
prefix the issue title with `Cursor researching`.

## Usage

Pipe a JSON automation payload into the script:

```bash
python3 linear_title_prefix.py < payload.json
```

Matching payloads print an `update_issue_title` action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5058",
  "title": "Cursor researching: Move the mb-data-manager into the psqo module"
}
```

Non-matching payloads print `null`.

## Development

Run the unit tests with:

```bash
python3 -m unittest -v
```

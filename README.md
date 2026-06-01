# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automations. When an issue moves to `to research`, it returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

## Usage

Pipe a Linear/Cursor automation payload into the CLI:

```sh
python3 linear_title_prefix.py < payload.json
```

For matching payloads, the command prints JSON like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4725",
  "title": "Cursor researching: UX Design of delivery chains"
}
```

Non-matching payloads print nothing and exit successfully.

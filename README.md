# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, the handler builds a
structured action that prefixes the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

For a matching payload, the command prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5094",
  "title": "Cursor researching: Refactor out the h2 provider into separate core hydrogen module"
}
```

For non-matching payloads, it prints `null`.

## Development

Run the unit tests with:

```bash
python3 -m unittest -v
```

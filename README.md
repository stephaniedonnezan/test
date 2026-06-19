# Linear issue research title automation

This repository contains a small handler for the Linear status-change automation
that prefixes an issue title with `Cursor researching` when the issue moves to
`To Research`.

## Behavior

`build_issue_title_update(event)` returns an action shaped like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4974",
  "title": "Cursor researching: User removal flow"
}
```

The handler:

- only acts on status/state/workflow-state changes to `To Research`;
- accepts Cursor `triggerContext` payloads and nested Linear webhook payloads;
- avoids duplicate `Cursor researching` prefixes; and
- leaves non-matching events unchanged by returning `None`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```

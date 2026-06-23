# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status-change event moves an issue to `To Research`, the helper
builds an action that prefixes the issue title with `Cursor researching`.

## Behavior

`build_issue_title_update(event)` returns an update action only when:

- the event is a status-change event or a Linear issue update whose changed
  fields include status/state/workflow state;
- the new status normalizes to `to research`;
- the issue has an id/identifier and a title; and
- the title does not already start with `Cursor researching`.

For matching events, it returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5036",
  "title": "Cursor researching: Mass Balance canvas items in delivery opacity off"
}
```

For non-matching events, it returns `null`.

## Development

Run the tests with:

```bash
python3 -m unittest -v
```

You can also pipe a JSON automation payload into the module:

```bash
python3 linear_title_prefix.py < payload.json
```

# Linear issue title prefix automation

This repository contains a small helper for Cursor/Linear automation payloads.
When a Linear issue status changes to `to research`, the helper builds an
issue title update that adds the `Cursor researching` prefix.

## Behavior

`build_issue_title_update(event)` returns an update action only when:

- the payload represents an issue status/state/workflow state change
- the new status normalizes to `to research`
- the issue has an id and title

Matching events return:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5063",
  "title": "Cursor researching: Improve performance of getPossibleQualifiedOutputItemsForLoadingEvent()"
}
```

Titles that already start with `Cursor researching` are left unchanged so the
prefix is not duplicated.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```

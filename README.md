# Linear issue research title prefix

This repository contains a small, side-effect-free helper for Cursor/Linear
automation payloads.

`linear_title_prefix.py` exposes `build_issue_title_update(event)`, which returns
an update action when a Linear issue status-change event enters `to research`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5037",
  "title": "Cursor researching: Able to delete supply contracts with connected meter readings"
}
```

The helper accepts flat Cursor `triggerContext` payloads and common nested Linear
webhook payloads. It normalizes status and trigger casing/separators, ignores
non-status updates, and skips titles that already start with `Cursor researching`
so repeated automation runs do not duplicate the marker.

## CLI usage

The module can also be used as a JSON stdin/stdout filter:

```sh
python3 linear_title_prefix.py < payload.json
```

It prints either the update action JSON or `null`.

## Tests

```sh
python3 -m unittest -v
```

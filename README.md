# Linear issue title automation

This repository contains a small helper for Linear issue status-change
automations.

When an issue status changes to `To Research`, `linear_title_prefix.py` returns
an update action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4895",
  "title": "Cursor researching: improve cascade rules for the psqo entity"
}
```

The helper accepts flat Cursor automation payloads and nested Linear webhook
payloads. It ignores non-status events, statuses other than `To Research`, and
titles that are already prefixed.

Run the tests with:

```sh
python3 -m unittest -v
```

You can also pipe a JSON event into the CLI:

```sh
python3 linear_title_prefix.py < event.json
```

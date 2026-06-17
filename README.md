# Linear issue title prefix automation

Adds a `Cursor researching` prefix to a Linear issue title when the issue status
changes to `to research`.

## Usage

Pass the Linear or Cursor automation payload on stdin:

```sh
python3 linear_title_prefix.py < payload.json
```

When the payload represents an issue status change to `to research`, the command
prints an update action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4963",
  "title": "Cursor researching: User role & rights cannot be seen by invitee"
}
```

Other payloads produce no output. Titles that already start with
`Cursor researching` are left unchanged.

## Verification

```sh
python3 -m unittest -v
```

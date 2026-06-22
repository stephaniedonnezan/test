# Linear issue title prefix automation

Builds an issue-title update action when a Cursor or Linear webhook reports
that an issue status changed to `to research`.

The action prefixes the issue title with `Cursor researching:` and does not add
the prefix again when it is already present.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

For matching events, the command prints JSON like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5047",
  "title": "Cursor researching: Always highlight the field that causes an error state"
}
```

For non-matching events, it prints nothing.

## Tests

```bash
python3 -m unittest -v
```

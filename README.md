# Linear title prefix automation

Adds `Cursor researching` to a Linear issue title when an issue status changes
to `to research`.

## Usage

Pass the automation payload as JSON on stdin. The script accepts both direct
Linear/Cursor payloads and Cursor Cloud `automation_trigger_info.triggerContext`
payloads.

```bash
python3 linear_title_prefix.py < payload.json
```

When the payload matches, the script prints an action object:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4931",
  "title": "Cursor researching: Stop allocation loops earlier"
}
```

For non-matching payloads, it prints `null`.

## Tests

```bash
python3 -m unittest -v
```

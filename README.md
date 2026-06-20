# Linear title prefix automation

Adds `Cursor researching` to a Linear issue title when an issue status changes
to `to research`.

The handler is implemented in `linear_title_prefix.py`. It reads webhook-style
payloads and returns a declarative action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5013",
  "title": "Cursor researching: Existing issue title"
}
```

## Test

```sh
python3 -m unittest -v
```

## CLI smoke check

```sh
printf '{"triggerContext":{"trigger":"status_changed","newStatus":"To Research","id":"POI-5013","title":"Loading message goes behind Mass Balance items"}}' \
  | python3 linear_title_prefix.py
```

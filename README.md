# Linear issue title automation

This repository provides a small helper script for Linear webhook payloads.

## Behavior

When the webhook payload indicates an issue `status_changed` event where the new
status is `to research`, the helper returns an updated issue title prefixed with:

`Cursor researching - `

The prefixing is idempotent (it will not add the prefix twice).

## Usage

Run with payload from stdin:

```bash
echo '{"triggerContext":{"trigger":"status_changed","newStatus":"to research","title":"Example issue"}}' | python3 linear_issue_title.py
```

Run with payload file:

```bash
python3 linear_issue_title.py --input payload.json
```

Output format:

```json
{"updatedTitle":"Cursor researching - Example issue"}
```

If no update is needed, the script returns:

```json
{"updatedTitle":null}
```

## Test

```bash
python3 -m unittest -v
```

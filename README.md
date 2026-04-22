# test

## Linear automation helper

This repository includes a small script that updates a Linear issue title when a
status-change webhook moves the issue to **"to research"**.

It prepends:

- `Cursor researching - `

to the issue title (if not already present).

### Usage

```bash
LINEAR_API_KEY="<linear api key>" \
TRIGGER_PAYLOAD='{"triggerContext":{"trigger":"status_changed","newStatus":"to research","id":"POI-4530","title":"My issue"}}' \
node ./src/run-linear-status-title-handler.mjs
```

`TRIGGER_PAYLOAD` should be the automation trigger JSON.

### Run tests

```bash
npm test
```

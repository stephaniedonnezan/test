# Linear issue title automation

This repository contains a small Linear status-change handler.

When a Linear issue status changes to `to research`, the handler updates the
issue title so it starts with `Cursor researching`.

## Usage

Provide a Linear API key or token in `LINEAR_API_KEY` or `LINEAR_API_TOKEN`.
Then pass the Linear webhook payload through one of:

- `LINEAR_WEBHOOK_PAYLOAD`
- `CURSOR_AUTOMATION_TRIGGER`
- `TRIGGER_CONTEXT`
- stdin

Run:

```sh
node scripts/linear-title-researching.mjs
```

The handler is idempotent: titles that already contain `Cursor researching`
are left unchanged.

## Tests

```sh
npm test
```

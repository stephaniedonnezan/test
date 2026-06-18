# Linear Cursor researching title helper

This repository contains a small Linear webhook helper that marks an issue title
when the issue status changes to `to research`.

For a Linear issue status-change payload like:

```json
{
  "triggerType": "linear",
  "webhookType": "issue",
  "trigger": "status_changed",
  "newStatus": "To Research",
  "id": "POI-4599",
  "title": "Cant close Jan 2025 for Trading Account"
}
```

the handler updates the issue title to:

```text
Cursor researching: Cant close Jan 2025 for Trading Account
```

The title update is idempotent; if the issue title already contains
`Cursor researching`, it is left unchanged.

## Usage

Install Node.js 18 or newer, set a Linear API key, and pipe the automation
payload into the CLI:

```sh
LINEAR_API_KEY=lin_api_... node src/index.js < payload.json
```

The CLI accepts either the trigger context directly or a wrapper object with a
`triggerContext` property.

## Tests

```sh
npm test
```

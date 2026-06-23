# Linear research title automation

This repository contains a small Node.js automation helper for Linear status-change
webhooks.

When a Linear issue status changes to `to research`, the helper updates the issue
title so it starts with:

```text
Cursor researching
```

For example:

```text
Remove Subscribe button on invite
```

becomes:

```text
Cursor researching: Remove Subscribe button on invite
```

The prefix is not duplicated if the title already starts with `Cursor researching`.

## Usage

Set a Linear API token and pass the webhook payload on stdin:

```sh
LINEAR_API_KEY=lin_api_... node src/linear-research-title.js < payload.json
```

For a safe local preview that does not call Linear:

```sh
node src/linear-research-title.js --dry-run < payload.json
```

The helper supports both Cursor automation payloads and standard Linear issue
webhook payloads.

## Tests

```sh
npm test
```

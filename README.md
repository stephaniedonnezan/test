# Linear research status title prefix

This repository contains a small automation helper for Linear issue webhooks.

When an issue status-change payload moves to `to research`, the helper returns
an issue title update action that prefixes the title with `Cursor researching`.
Existing `Cursor researching` prefixes are left unchanged so repeated webhook
deliveries are idempotent.

## Usage

```js
const { handleIssueStatusChanged } = require("./src");

const action = handleIssueStatusChanged({
  triggerContext: {
    trigger: "status_changed",
    newStatus: "to research",
    id: "POI-4206",
    title: "[][Dev] - PoS document handling",
  },
});

// {
//   action: "update_issue_title",
//   issueId: "POI-4206",
//   issueUrl: undefined,
//   previousTitle: "[][Dev] - PoS document handling",
//   title: "Cursor researching: [][Dev] - PoS document handling"
// }
```

## Testing

```bash
npm test
```

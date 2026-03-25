# Linear webhook title updater

This repository contains a small webhook handler that updates a Linear issue title when an issue status changes to **To Research**.

## Behavior

When Linear sends an Issue `update` webhook and the issue state transitions into `To Research`, the handler updates the issue title to add:

`Cursor researching: `

The update is idempotent: if the title already starts with `Cursor researching` (case-insensitive), no API call is made.

## Setup

1. Install dependencies:

```bash
npm install
```

2. Set your Linear API key:

```bash
export LINEAR_API_KEY="your_linear_api_key"
```

## Run tests

```bash
npm test
```

## Local usage

Pass a webhook JSON payload as a single CLI argument:

```bash
node src/index.js '{"type":"Issue","action":"update","data":{"id":"POI-4178","title":"Example","previous":{"state":{"name":"Todo"}},"state":{"name":"To Research"}}}'
```

The script prints a JSON result object describing whether a title change was made.

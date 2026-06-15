# Linear research title prefix automation

Adds `Cursor researching` to a Linear issue title when an issue status changes to
`to research`.

For a matching status-change payload, the automation updates:

```text
Issue title
```

to:

```text
Cursor researching: Issue title
```

If the title already starts with `Cursor researching`, the automation leaves it
unchanged.

## Usage

Set `LINEAR_API_KEY`, then pass a Linear webhook payload as JSON:

```sh
node src/index.js '{"triggerContext":{"trigger":"status_changed","newStatus":"To Research","id":"POI-4178","title":"Example"}}'
```

## Tests

```sh
npm test
```

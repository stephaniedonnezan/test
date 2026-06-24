# Linear issue title automation

Builds an issue-title update when a Linear status-change event moves an issue to
`to research`.

The handler prefixes the issue title with `Cursor researching` and leaves titles
that already have that prefix unchanged.

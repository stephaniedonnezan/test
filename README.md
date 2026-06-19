# Linear issue title prefix automation

Builds an issue-title update action when a Linear issue status changes to
`to research`.

The handler prefixes eligible titles with:

```text
Cursor researching: <original title>
```

It ignores unrelated status changes and titles that already start with the
prefix.

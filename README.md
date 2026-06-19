# Linear issue title prefix automation

Adds a `Cursor researching` title prefix when a Linear issue status changes to
`to research`.

## Usage

Pipe a Linear/Cursor automation payload into the handler:

```sh
python3 linear_title_prefix.py < payload.json
```

When the payload represents a status transition to `to research`, the handler
prints an `update_issue_title` action. Other events produce no output.

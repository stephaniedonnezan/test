# Linear research title automation

This repository contains a small helper for updating Linear issue titles when an
issue moves into the `to research` status.

## Behavior

`scripts/linear_research_title.py` reads a Linear or Cursor automation webhook
payload. When the payload represents an issue status change into `to research`,
the helper prefixes the issue title with:

```text
Cursor researching
```

The update is idempotent: titles that already start with `Cursor researching`
are left unchanged.

## Usage

Provide a Linear API key and pass the webhook payload on stdin:

```sh
export LINEAR_API_KEY=lin_api_...
python3 scripts/linear_research_title.py < payload.json
```

For local validation without writing to Linear:

```sh
python3 scripts/linear_research_title.py --dry-run < payload.json
```

## Tests

```sh
python3 -m unittest discover -s tests
```

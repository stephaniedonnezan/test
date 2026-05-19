# Linear research title helper

This repository contains a small helper for Linear status-change webhooks.

When an issue status changes to `to research`, `linear_research_title.py` updates
the issue title so it contains `[Cursor researching]`. It is idempotent and turns
titles such as `[]Site switch on the site name` into
`[Cursor researching] Site switch on the site name`.

## Usage

Provide the webhook payload on stdin or in `AUTOMATION_TRIGGER_INFO`, and set a
Linear API key with issue update permissions:

```bash
export LINEAR_API_KEY=lin_api_...
python3 linear_research_title.py < payload.json
```

The helper exits without changing the issue unless the normalized status is
`to research`.

## Tests

```bash
python3 -m unittest
```

# test

## Linear automation helper

This repository contains a small helper for processing Linear issue webhook payloads.

Implemented rule:
- When `triggerContext.trigger == "status_changed"` and `triggerContext.newStatus == "to research"`, update the issue title to include `Cursor researching`.

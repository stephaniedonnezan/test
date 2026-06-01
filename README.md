# Linear title prefix automation

Builds a title-update action for Linear issue payloads when an issue status
changes to `to research`.

The handler prefixes eligible issue titles with `Cursor researching` while
leaving already-prefixed titles unchanged.

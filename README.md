# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when a status-change event moves
the issue to `to research`.

The handler is intentionally side-effect free: it returns an update action for the
caller to apply to Linear, or `None` when no title change is needed.

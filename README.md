# Linear issue title automation

This repository contains a small handler for the Cursor/Linear automation that
adds `Cursor researching` to an issue title when the issue moves to the
`to research` status.

The handler is side-effect free: it returns the title update action that the
automation runner can execute.

```bash
python3 -m unittest -v
```

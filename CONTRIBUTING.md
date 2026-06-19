# Contributing

Contributions should preserve the core boundary: Hermos may produce context,
signals, policies, and evidence, but it must not silently execute retries,
modify host files, or write private data.

Before opening a change:

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
```

Use synthetic names and projects in tests. Never commit real user profiles,
conversation logs, credentials, home-directory paths, or private memory files.

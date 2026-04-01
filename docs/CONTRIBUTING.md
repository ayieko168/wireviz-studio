# Contribution Guidelines

Thank you for contributing to WireViz Studio.

## Before Opening a PR

1. Search existing issues and pull requests for related work.
2. Open an issue when proposing larger behavior changes.
3. For bug reports, include:
   - OS version
   - Python version
   - GraphViz version from `dot -V`
   - A minimal reproducible YAML example
   - Full traceback or error output

## Development Setup

Use the project virtual environment at `./venv`.

```powershell
./venv/Scripts/python.exe -m pip install --upgrade pip
./venv/Scripts/python.exe -m pip install -e ".[gui,test]"
```

Run tests before submitting:

```powershell
./venv/Scripts/python.exe -m pytest tests/core -q
```

## Pull Request Checklist

1. Keep changes focused and scoped to one purpose.
2. Add or update tests for behavior changes.
3. Update docs when changing workflows or syntax.
4. Do not commit generated packaging outputs.
5. Ensure CI is green.

If you change YAML syntax behavior, update `docs/syntax.md` in the same PR.

## Style and Quality

- Keep code readable and maintainable.
- Prefer explicit names and small functions.
- Follow existing project patterns in `src/wireviz_studio` and `tests/core`.
- Use Google-style docstrings when adding public APIs.

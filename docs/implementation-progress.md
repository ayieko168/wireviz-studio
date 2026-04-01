# WireViz Studio Implementation Progress

This file is the physical progress log for the transformation plan.

## Phase Status

- [x] Phase 1 - Project Restructure and Core Refactor
- [ ] Phase 2 - GraphViz Binary Management
- [ ] Phase 3 - PySide6 GUI
- [ ] Phase 4 - Testing
- [ ] Phase 5 - CI/CD and Packaging
- [ ] Phase 6 - Documentation

## Phase 1 Detail

- [x] Step 1.1: Create planned package and support directory structure
- [x] Step 1.2: Replace legacy packaging setup with `pyproject.toml` metadata and tool config
- [x] Step 1.3: Move core implementation into `wireviz_studio.core` and expose native render/parser APIs
- [x] Step 1.4: Remove old CLI-oriented files (`wv_cli.py`, `build_examples.py`)

## Notes

- `wireviz_studio` now contains the planned top-level Phase 1 package skeleton: `core`, `gui`, `graphviz_manager`, and `export`.
- `wireviz_studio.core` no longer imports implementation from `src/wireviz`; the migrated code now lives in the new package.
- Removed legacy source tree `src/wireviz` to keep only Studio-focused code.
- Replaced `.gitkeep` markers with actual placeholder files in `tests/fixtures` and `packaging`.
- Normalized several copied core internals to clearer snake_case local variable names without changing logical flow.
- Pruned obvious non-runtime GraphViz bundle content (`include`, `share/man`, `lib/pkgconfig`, `lib/cmake`, `.lib`, sample `share/graphviz/graphs`) and verified bundled `dot.exe` still renders SVG.
- Validation: `./venv/Scripts/python.exe -m pytest tests/core -q` passed on 2026-04-01.
- Rendering now raises `GraphVizNotFoundError` when the `dot` executable is unavailable; bundled/system GraphViz resolution remains Phase 2 work.

# WireViz Studio Implementation Progress

This file is the physical progress log for the transformation plan.

## Phase Status

- [x] Phase 1 - Project Restructure and Core Refactor
- [x] Phase 2 - GraphViz Binary Management
- [x] Phase 3 - PySide6 GUI
- [ ] Phase 4 - Testing
- [ ] Phase 5 - CI/CD and Packaging
- [ ] Phase 6 - Documentation

## Phase 2 Detail

- [x] Step 2.1: Implemented `graphviz_manager` resolution order (bundled -> system -> error)
- [x] Step 2.1: Added `dot -V` verification and environment setup (`GRAPHVIZ_DOT`, `PATH`)
- [x] Step 2.1: Integrated resolver into `Harness.render_svg()` / `Harness.render_png()`
- [x] Step 2.2: Added checksum-verified archive downloader utility and CI-friendly script scaffold

## Phase 3 Detail

- [x] Step 3.1: Implemented `MainWindow` shell with menus, toolbar, splitter, and status bar
- [x] Step 3.2: Implemented multi-tab YAML editor with line numbers and syntax highlighting
- [x] Step 3.3: Implemented tabbed preview panel with diagram view and BOM table
- [x] Step 3.4: Implemented `RenderWorker(QThread)` with parse/render success and error signals
- [x] Step 3.5: Implemented export dialog UI (selection flow); backend export execution deferred
- [x] Step 3.6: Implemented light/dark theme files and runtime application
- [x] Step 3.7: Implemented `QSettings` wrapper for theme, recent files, geometry/state, splitter sizes, and export prefs

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
- Validation (Phase 2): `./venv/Scripts/python.exe -m pytest tests/core -q` passed with 4 tests.
- GraphViz resolution now prefers bundled binaries, then system install, then raises `GraphVizNotFoundError`.
- Validation (Phase 3): GUI modules import cleanly (`PYTHONPATH=src`, import `wireviz_studio.gui.app`) and core tests remain green.

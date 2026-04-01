# Plan: WireViz Studio — CLI to PySide6 GUI Transformation

Transform WireViz CLI (v0.4.1) into **WireViz Studio**, a cross-platform PySide6 desktop app with a multi-tab YAML editor, manual-refresh diagram preview, tabbed BOM viewer, and multi-format export. Bundle GraphViz binaries for frictionless install. Restructure into a clean layout, add pytest core tests, CI/CD for 4 installer targets, light/dark theme, and a GitHub Pages landing page.

---

## Decisions (from Q&A)

| Topic | Decision |
|---|---|
| App name | WireViz Studio |
| GraphViz | Bundle binaries (v1); later add auto-detect + download |
| Editor | QPlainTextEdit + YAML syntax highlighter |
| Preview | Manual refresh (Render button) |
| Export formats | PNG, SVG, PDF (diagram / BOM / both), CSV (BOM) |
| Installers | Win .exe (Inno Setup), Win portable .zip, macOS .dmg, Linux .AppImage |
| BOM display | Tabbed panel: Diagram tab ↔ BOM tab |
| Tests | Core engine only (initially) |
| Python floor | 3.10 |
| File management | Multi-tab editor |
| Themes | Light (default) + Dark toggle |
| GitHub Pages | Landing page with screenshots + download links |
| License | GPLv3 |
| Settings | QSettings (native per platform) |
| PDF engine | QPrinter (built-in) |
| Onboarding | None (docs only) |

---

## Phase 1 — Project Restructure & Core Refactor

### Step 1.1: New directory structure

```
wireviz-studio/
├── .github/workflows/          # ci.yml, release.yml, pages.yml
├── docs/                       # GitHub Pages site + syntax.md
├── src/wireviz_studio/
│   ├── __init__.py             # __version__, APP_NAME
│   ├── __main__.py             # GUI entry point
│   ├── core/                   # Pure engine — no GUI, no I/O
│   │   ├── parser.py           # YAML → Harness (extracted from wireviz.py)
│   │   ├── harness.py          # Harness + render_svg() / render_png()
│   │   ├── models.py           # All dataclasses
│   │   ├── bom.py              # BOM generation
│   │   ├── colors.py           # Color codes
│   │   ├── graphviz_html.py    # GV HTML-label helpers
│   │   ├── svg_embed.py        # SVG image embedding
│   │   ├── exceptions.py       # WireVizStudioError hierarchy
│   │   └── helpers.py          # Pure utilities
│   ├── gui/                    # PySide6 layer
│   │   ├── app.py              # QApplication + theme loading
│   │   ├── main_window.py      # QMainWindow, menus, toolbar
│   │   ├── editor.py           # Multi-tab QPlainTextEdit
│   │   ├── highlighter.py      # YAML QSyntaxHighlighter
│   │   ├── preview.py          # Diagram (QSvgWidget) + BOM tabs
│   │   ├── export.py           # Export dialog
│   │   ├── settings.py         # QSettings wrapper
│   │   ├── worker.py           # QThread render worker
│   │   └── themes/             # light.qss, dark.qss
│   ├── graphviz_manager/       # Binary detection/bundling
│   │   ├── bundled.py          # Locate bundled dot binary
│   │   ├── detect.py           # Find system GraphViz
│   │   └── download.py         # (v2) Download + verify
│   └── export/                 # Export renderers
│       ├── png_export.py
│       ├── svg_export.py
│       ├── pdf_export.py       # QPrinter: diagram / BOM / both
│       └── csv_export.py
├── tests/
│   ├── core/                   # test_parser, test_harness, test_bom, etc.
│   └── fixtures/               # YAML inputs + expected outputs
├── examples/                   # Curated 4-6 demos
├── bundled_graphviz/           # Platform binaries (gitignored, added in CI)
├── packaging/                  # inno_setup.iss, AppImage, macOS
├── pyproject.toml              # Full PEP 621
└── README.md
```

### Step 1.2: Migrate to `pyproject.toml`

Full PEP 621 with pinned deps, ruff, pytest config. Delete `setup.py`. *(parallel with 1.1)*

### Step 1.3: Core engine refactor

Key changes to existing code:

- Extract YAML parsing from `wireviz.parse()` lines 111–227 into `core/parser.py :: parse_yaml(data: dict) -> Harness` — pure function, no file I/O
- Split `Harness.output()` into `render_svg() -> str` and `render_png() -> bytes` — in-memory only, no temp files
- File writing moves entirely to `export/` layer
- Add `core/exceptions.py`: `WireVizStudioError` → `YAMLParseError`, `ValidationError`, `RenderError`, `GraphVizNotFoundError`
- The existing `harness.svg` property already does in-memory SVG render — build on that pattern

### Step 1.4: Remove CLI

Delete `wv_cli.py`, `build_examples.py`, remove console_scripts. *(parallel with 1.3)*

---

## Phase 2 — GraphViz Binary Management

### Step 2.1: `graphviz_manager/` package

- Resolution order: **bundled → system-installed → error dialog**
- `bundled.py`: looks for `dot` in `bundled_graphviz/{platform}/` relative to app root, sets `GRAPHVIZ_DOT` env var
- `detect.py`: scans PATH + common install dirs (e.g. `C:\Program Files\Graphviz\bin\` on Windows), runs `dot -V` to verify
- v1 ships with pre-bundled binaries (~30MB per platform, downloaded in CI)

### Step 2.2: CI download scripts

Download official GraphViz release per platform during the packaging workflow, verify SHA256 checksums. *(parallel with 2.1)*

---

## Phase 3 — PySide6 GUI

### Step 3.1: App shell

`MainWindow(QMainWindow)` with:

- Menu bar: File (New/Open/Save/Save As/Recent/Close Tab/Exit), View (Theme toggle/Zoom), Tools (Render/Export), Help (About/Syntax Ref)
- Toolbar: New, Open, Save, **Render**, **Export** — rounded buttons, icons, tooltips
- Central: `QSplitter` → editor left, preview right
- Status bar: parse status, GraphViz version, file path

### Step 3.2: Multi-tab editor

`QTabWidget` of `QPlainTextEdit` instances, each with:

- Line numbers, dirty indicator (`*` in tab title), close buttons
- `YamlHighlighter`: keys bold, strings/numbers/booleans/comments colored, WireViz keywords (`connectors`, `cables`, `connections`) accented
- Standard keyboard shortcuts (Ctrl+S, Ctrl+W, Ctrl+Tab)

### Step 3.3: Preview panel

`QTabWidget` with:

- **Diagram tab**: `QGraphicsView` + `QGraphicsSvgItem` with scroll + mouse-wheel zoom + fit-to-window button
- **BOM tab**: `QTableWidget`, sortable columns, copy-to-clipboard

### Step 3.4: Render worker

`RenderWorker(QThread)`:

1. Takes YAML string → `parse_yaml()` → `harness.render_svg()` → emits `render_complete(svg, bom)`
2. Catches all exceptions → emits `render_error(WireVizStudioError)` → status bar + error highlight
3. Thread-safe: each render creates its own Harness (no shared mutable state)

### Step 3.5: Export system

`ExportDialog(QDialog)`:

- Format selector: PNG, SVG, PDF, CSV
- PDF sub-options: *Diagram only* / *BOM only* / *Diagram + BOM* (radio buttons)
- Output path picker
- All exports run on QThread with status bar progress

### Step 3.6: Themes

`light.qss` (default) and `dark.qss`:

- Slightly rounded buttons (`border-radius: 4px`), clear labels, tooltips everywhere
- WCAG AA contrast ratios for dark theme
- Toggle via View menu → persisted in QSettings

### Step 3.7: Settings

`AppSettings` wrapping QSettings: theme, recent_files (max 10), window geometry/state, splitter sizes, last export dir/format

---

## Phase 4 — Testing

### Step 4.1: Test infrastructure

pytest + pytest-cov, fixtures from curated YAML files

### Step 4.2: Core tests

Engine only, no GUI tests for v1:

| Test file | Covers |
|---|---|
| `test_parser.py` | Valid YAML → correct Harness; invalid YAML → `YAMLParseError`; missing pins → `ValidationError` |
| `test_harness.py` | `render_svg()` returns valid SVG; `render_png()` returns PNG bytes; connection wiring |
| `test_models.py` | Connector/Cable `__post_init__` validation, Image aspect ratio |
| `test_bom.py` | Deduplication, qty_multiplier, sorting |
| `test_colors.py` | Color translation, color code lookups |

---

## Phase 5 — CI/CD & Packaging

### Step 5.1: CI workflow

On PR/push: matrix (Python 3.10–3.12 × Win/Mac/Linux), ruff lint, pytest, coverage

### Step 5.2: Release workflow

On tag `v*`, three parallel jobs:

| Platform | Build | Artifacts |
|---|---|---|
| Windows | PyInstaller `--onedir` + Inno Setup | `.exe` installer + portable `.zip` |
| macOS | PyInstaller `--onedir --windowed` + `create-dmg` | `.dmg` |
| Linux | PyInstaller `--onedir` + `appimagetool` | `.AppImage` |

Each job downloads GraphViz binaries for its platform and bundles them. Final job creates GitHub Release with all artifacts.

### Step 5.3: GitHub Pages

Static landing page: hero screenshot, platform download buttons, feature bullets, links to docs

---

## Phase 6 — Documentation

### Step 6.1: README rewrite

Concise: what it is, screenshot, install links (3 platforms), quick start (5 steps), build from source, license

### Step 6.2: Curate examples

Keep 4–6 best demos, rest become test fixtures

### Step 6.3: Syntax reference

Update for Studio context, add screenshots

---

## File Migration Map

| Current | Action | New |
|---|---|---|
| `src/wireviz/wireviz.py` | Split | `core/parser.py` (parsing) + `export/` (file output) |
| `src/wireviz/Harness.py` | Refactor | `core/harness.py` — split `output()` into `render_svg()`, `render_png()` |
| `src/wireviz/DataClasses.py` | Move | `core/models.py` |
| `src/wireviz/wv_bom.py` | Move | `core/bom.py` |
| `src/wireviz/wv_colors.py` | Move | `core/colors.py` |
| `src/wireviz/wv_gv_html.py` | Move | `core/graphviz_html.py` |
| `src/wireviz/wv_helper.py` | Split | `core/helpers.py` (pure), file I/O → export layer |
| `src/wireviz/svgembed.py` | Move | `core/svg_embed.py` |
| `src/wireviz/wv_html.py` | Delete | Replaced by GUI + QPrinter |
| `src/wireviz/wv_cli.py` | Delete | Replaced by GUI |
| `src/wireviz/build_examples.py` | Delete | Replaced by pytest |
| `setup.py` | Delete | Replaced by `pyproject.toml` |

---

## Verification Checklist

1. `pytest tests/core/ -v` — all green
2. Parse `demo01.yml` → SVG contains "X1", "X2", "W1"
3. App launches on each platform, shows empty editor
4. Open `.yml` → tab appears → Render → diagram + BOM populate
5. Export each format → valid output file
6. Theme toggle → all widgets restyle
7. Invalid YAML → status bar error, no crash
8. Missing GraphViz → clear error dialog
9. Install from `.exe`/`.dmg`/`.AppImage` on clean machine → works
10. CI matrix all green

---

## Scope — Excluded from v1

- Form-based visual editor / drag-and-drop
- Live-preview-on-typing
- YAML autocomplete
- Auto-update mechanism
- i18n / localization
- Plugin system

---

## UI Wireframe

```
┌──────────────────────────────────────────────────────────────────┐
│ File   Edit   View   Tools   Help                         ─ □ ✕ │
├──────────────────────────────────────────────────────────────────┤
│ [📄 New] [📂 Open] [💾 Save]  ║  [▶ Render] [📤 Export]        │
├────────────────────────────┬─────────────────────────────────────┤
│  demo01.yml ✕ │ demo02.yml*│   [📊 Diagram] [📋 BOM]           │
├────────────────────────────┤─────────────────────────────────────┤
│  1│ connectors:            │                                     │
│  2│   X1:                  │     ┌─────────┐   ┌─────────┐      │
│  3│     type: D-Sub        │     │   X1    │───│   X2    │      │
│  4│     subtype: female    │     │  D-Sub  │ W1│ Molex   │      │
│  5│     pinlabels: [...]   │     └─────────┘   └─────────┘      │
│  6│   X2:                  │                                     │
│  7│     type: Molex KK 254 │           (SVG diagram)             │
│  8│ cables:                │                                     │
│  9│   W1:                  │                         [Fit 🔍]    │
├────────────────────────────┴─────────────────────────────────────┤
│ ✓ Rendered successfully  │  GraphViz 12.2.1  │  demo01.yml      │
└──────────────────────────────────────────────────────────────────┘
```

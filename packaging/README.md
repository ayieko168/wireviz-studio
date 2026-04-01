Packaging assets and scripts for release workflows.

## Current Packaging Flow

- CI workflow: `.github/workflows/main.yml`
	- Runs ruff + pytest core matrix across Windows/macOS/Linux and Python 3.10-3.13.
- Release workflow: `.github/workflows/release.yml`
	- Triggers on `v*` tags.
	- Builds platform-specific portable bundles with PyInstaller.
	- Uses the pushed tag as the artifact version label (for example, tag `v1.2.0` -> artifact `...-1.2.0-...`).
	- Publishes archives as GitHub Release assets.

## Build Output Layout

PyInstaller working output is centralized under:

- `build/packaging/<build-type>/<platform>/spec/`
- `build/packaging/<build-type>/<platform>/work/`
- `build/packaging/<build-type>/<platform>/dist/`

Final distributable archives are written to:

- `dist-artifacts/<build-type>/<platform>/<python-tag>/`

Archive names are explicit and include version/build/platform/python, for example:

- `wireviz-studio-0.1.0a0-portable-windows-py3.12.zip`

## Local Portable Build

From repository root:

```powershell
./venv/Scripts/python.exe -m pip install ".[gui]"
./venv/Scripts/python.exe -m pip install pyinstaller==6.16.0
./venv/Scripts/python.exe packaging/build_portable.py --build-type portable --clean
```

Output archives are written to `dist-artifacts/`.

## Local Native Builds (Phase 5 Packaging Extension C)

Native targets use `packaging/build_native.py` and produce platform-specific artifacts:

- Windows: NSIS installer (`.exe`)
- macOS: DMG (`.dmg`)
- Linux: AppImage (`.AppImage`)

### Windows Installer

Requirements:

- NSIS (`makensis`) available in PATH

Command:

```powershell
./venv/Scripts/python.exe packaging/build_native.py --target windows-installer --clean
```

Optional signing environment variables:

- `WINDOWS_SIGN_CERT_SHA1`
- `WINDOWS_TIMESTAMP_URL` (defaults to `http://timestamp.digicert.com`)

### macOS DMG

Command:

```bash
./venv/Scripts/python.exe packaging/build_native.py --target macos-dmg --clean
```

Optional signing/notarization environment variables:

- `APPLE_CODESIGN_IDENTITY`
- `APPLE_NOTARY_PROFILE`

### Linux AppImage

Requirements:

- `appimagetool` available in PATH or provided via `APPIMAGETOOL`

Command:

```bash
./venv/Scripts/python.exe packaging/build_native.py --target linux-appimage --clean
```

Optional detached signature toggle:

- `GPG_SIGN_APPIMAGE=1` (when GPG key is already loaded)

## Cleanup Generated Outputs

Use the dedicated cleanup script from repository root:

```powershell
./venv/Scripts/python.exe packaging/clean_build_outputs.py
```

Optional modes:

- Include caches (`.coverage`, `.pytest_cache`, `.ruff_cache`):

```powershell
./venv/Scripts/python.exe packaging/clean_build_outputs.py --include-caches
```

- Preview only (no deletions):

```powershell
./venv/Scripts/python.exe packaging/clean_build_outputs.py --dry-run
```

## Why `".[gui]"` Is Used

`gui` is an optional dependency extra defined in `pyproject.toml` under `[project.optional-dependencies]`.

- `python -m pip install ".[gui]"` installs the base package plus GUI dependencies (currently PySide6).
- Quoting is recommended in PowerShell and CI scripts to avoid bracket wildcard interpretation.

"""Build native WireViz Studio installers for each platform.

Targets:
- windows-installer: NSIS .exe installer
- macos-dmg: Apple disk image containing .app bundle
- linux-appimage: AppImage bundle

The script can run locally or in CI. Signing/notarization hooks are optional and
enabled only when the relevant environment variables are set.
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST_ARTIFACTS = ROOT / "dist-artifacts"
APP_NAME = "WireVizStudio"
DISPLAY_NAME = "WireViz Studio"


def _run(command: list[str], cwd: Path | None = None) -> None:
    subprocess.run(command, check=True, cwd=cwd or ROOT)


def _data_separator() -> str:
    return ";" if platform.system().lower().startswith("win") else ":"


def _platform_tag() -> str:
    system = platform.system().lower()
    if system.startswith("win"):
        return "windows"
    if system == "darwin":
        return "macos"
    return "linux"


def _python_tag() -> str:
    return f"py{sys.version_info.major}.{sys.version_info.minor}"


def _project_version() -> str:
    init_file = ROOT / "src" / "wireviz_studio" / "__init__.py"
    text = init_file.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        return "0.0.0"
    return match.group(1)


def _normalized_version(version_text: str) -> str:
    if not version_text:
        return _project_version()
    return version_text[1:] if version_text.startswith("v") else version_text


def _build_dirs(target: str) -> dict[str, Path]:
    base = ROOT / "build" / "packaging" / target / _platform_tag()
    return {
        "base": base,
        "spec": base / "spec",
        "work": base / "work",
        "dist": base / "dist",
        "native": base / "native",
    }


def _artifact_dir(target: str) -> Path:
    return DIST_ARTIFACTS / target / _platform_tag() / _python_tag()


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build native WireViz Studio packages")
    parser.add_argument(
        "--target",
        required=True,
        choices=["windows-installer", "macos-dmg", "linux-appimage"],
        help="Native package target to build",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove previous outputs for this target/platform before building",
    )
    parser.add_argument(
        "--version",
        default="",
        help="Optional version override for artifact names (example: v1.2.3)",
    )
    return parser.parse_args()


def _run_pyinstaller(target: str) -> Path:
    dirs = _build_dirs(target)
    sep = _data_separator()
    themes_src = ROOT / "src" / "wireviz_studio" / "gui" / "themes"

    add_data_args = [f"{themes_src}{sep}wireviz_studio/gui/themes"]
    bundled_graphviz = ROOT / "bundled_graphviz"
    if bundled_graphviz.exists():
        add_data_args.append(f"{bundled_graphviz}{sep}bundled_graphviz")

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(dirs["dist"]),
        "--workpath",
        str(dirs["work"]),
        "--specpath",
        str(dirs["spec"]),
        "--paths",
        "src",
        "--collect-submodules",
        "wireviz_studio",
    ]

    for add_data in add_data_args:
        command.extend(["--add-data", add_data])

    command.append("src/wireviz_studio/__main__.py")
    _run(command)

    if _platform_tag() == "macos":
        app_bundle = dirs["dist"] / f"{APP_NAME}.app"
        if app_bundle.exists():
            return app_bundle

    app_dir = dirs["dist"] / APP_NAME
    if not app_dir.exists():
        raise FileNotFoundError(f"Expected PyInstaller output missing: {app_dir}")
    return app_dir


def _build_windows_installer(app_dir: Path, target: str, version_text: str) -> Path:
    if _platform_tag() != "windows":
        raise RuntimeError("windows-installer target can only run on Windows")

    makensis = shutil.which("makensis")
    if not makensis:
        raise RuntimeError("makensis not found. Install NSIS and ensure it is in PATH.")

    dirs = _build_dirs(target)
    dirs["native"].mkdir(parents=True, exist_ok=True)
    artifact_dir = _artifact_dir(target)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    out_file = artifact_dir / (
        f"wireviz-studio-{_normalized_version(version_text)}-installer-"
        f"{_platform_tag()}-{_python_tag()}.exe"
    )

    nsis_script = dirs["native"] / "installer.nsi"
    nsis_script.write_text(
        (
            "Unicode True\n"
            "Name \"WireViz Studio\"\n"
            f"OutFile \"{out_file}\"\n"
            "InstallDir \"$PROGRAMFILES64\\WireViz Studio\"\n"
            "RequestExecutionLevel admin\n"
            "SetCompressor /SOLID lzma\n"
            "\n"
            "!include \"MUI2.nsh\"\n"
            "!insertmacro MUI_PAGE_WELCOME\n"
            "!insertmacro MUI_PAGE_DIRECTORY\n"
            "!insertmacro MUI_PAGE_INSTFILES\n"
            "!insertmacro MUI_PAGE_FINISH\n"
            "!insertmacro MUI_UNPAGE_CONFIRM\n"
            "!insertmacro MUI_UNPAGE_INSTFILES\n"
            "!insertmacro MUI_LANGUAGE \"English\"\n"
            "\n"
            "Section \"Install\"\n"
            "  SetOutPath \"$INSTDIR\"\n"
            f"  File /r \"{app_dir}\\*\"\n"
            "  CreateDirectory \"$SMPROGRAMS\\WireViz Studio\"\n"
            "  CreateShortCut \"$SMPROGRAMS\\WireViz Studio\\WireViz Studio.lnk\" \"$INSTDIR\\WireVizStudio.exe\"\n"
            "  CreateShortCut \"$DESKTOP\\WireViz Studio.lnk\" \"$INSTDIR\\WireVizStudio.exe\"\n"
            "  WriteUninstaller \"$INSTDIR\\Uninstall.exe\"\n"
            "SectionEnd\n"
            "\n"
            "Section \"Uninstall\"\n"
            "  Delete \"$DESKTOP\\WireViz Studio.lnk\"\n"
            "  Delete \"$SMPROGRAMS\\WireViz Studio\\WireViz Studio.lnk\"\n"
            "  RMDir \"$SMPROGRAMS\\WireViz Studio\"\n"
            "  RMDir /r \"$INSTDIR\"\n"
            "SectionEnd\n"
        ),
        encoding="utf-8",
    )

    _run([makensis, str(nsis_script)])

    # Optional Authenticode signing when signtool + cert metadata are available.
    signtool = shutil.which("signtool")
    cert_sha1 = os.getenv("WINDOWS_SIGN_CERT_SHA1", "").strip()
    timestamp_url = os.getenv("WINDOWS_TIMESTAMP_URL", "http://timestamp.digicert.com").strip()
    if signtool and cert_sha1:
        _run(
            [
                signtool,
                "sign",
                "/sha1",
                cert_sha1,
                "/fd",
                "SHA256",
                "/tr",
                timestamp_url,
                "/td",
                "SHA256",
                str(out_file),
            ]
        )

    return out_file


def _build_macos_dmg(app_output: Path, target: str, version_text: str) -> Path:
    if _platform_tag() != "macos":
        raise RuntimeError("macos-dmg target can only run on macOS")

    hdiutil = shutil.which("hdiutil")
    if not hdiutil:
        raise RuntimeError("hdiutil is not available on this machine.")

    artifact_dir = _artifact_dir(target)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    dmg_file = artifact_dir / (
        f"wireviz-studio-{_normalized_version(version_text)}-dmg-"
        f"{_platform_tag()}-{_python_tag()}.dmg"
    )

    app_bundle = app_output
    if app_bundle.suffix != ".app":
        candidate = app_output.parent / f"{APP_NAME}.app"
        if candidate.exists():
            app_bundle = candidate
        else:
            raise FileNotFoundError(f"Expected .app bundle not found: {candidate}")

    # Optional Developer ID signing for notarization workflows.
    identity = os.getenv("APPLE_CODESIGN_IDENTITY", "").strip()
    if identity:
        _run(
            [
                "codesign",
                "--force",
                "--deep",
                "--options",
                "runtime",
                "--sign",
                identity,
                str(app_bundle),
            ]
        )

    _run(
        [
            hdiutil,
            "create",
            "-volname",
            DISPLAY_NAME,
            "-srcfolder",
            str(app_bundle),
            "-ov",
            "-format",
            "UDZO",
            str(dmg_file),
        ]
    )

    # Optional notarization and stapling via preconfigured keychain profile.
    notary_profile = os.getenv("APPLE_NOTARY_PROFILE", "").strip()
    if notary_profile:
        profile_check = subprocess.run(
            ["xcrun", "notarytool", "history", "--keychain-profile", notary_profile],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if profile_check.returncode == 0:
            _run(
                [
                    "xcrun",
                    "notarytool",
                    "submit",
                    str(dmg_file),
                    "--keychain-profile",
                    notary_profile,
                    "--wait",
                ]
            )
            _run(["xcrun", "stapler", "staple", str(dmg_file)])
        else:
            print(f"Notary profile '{notary_profile}' not found; skipping notarization.")

    return dmg_file


def _make_linux_icon(icon_path: Path) -> None:
    from PIL import Image, ImageDraw

    icon_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (256, 256), (29, 53, 87, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((52, 52, 204, 204), outline=(168, 218, 220, 255), width=12)
    draw.line((80, 176, 176, 80), fill=(241, 250, 238, 255), width=14)
    image.save(icon_path)


def _build_linux_appimage(app_dir: Path, target: str, version_text: str) -> Path:
    if _platform_tag() != "linux":
        raise RuntimeError("linux-appimage target can only run on Linux")

    appimagetool = os.getenv("APPIMAGETOOL", "").strip() or shutil.which("appimagetool")
    if not appimagetool:
        raise RuntimeError("appimagetool not found. Set APPIMAGETOOL or install appimagetool.")

    dirs = _build_dirs(target)
    appdir = dirs["native"] / f"{APP_NAME}.AppDir"
    _remove_path(appdir)
    (appdir / "usr" / "bin").mkdir(parents=True, exist_ok=True)

    # Copy all PyInstaller runtime files into AppDir/usr/bin.
    for item in app_dir.iterdir():
        dest = appdir / "usr" / "bin" / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    apprun = appdir / "AppRun"
    apprun.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "HERE=$(dirname \"$(readlink -f \"$0\")\")\n"
        f"exec \"$HERE/usr/bin/{APP_NAME}\" \"$@\"\n",
        encoding="utf-8",
    )
    apprun.chmod(0o755)

    desktop = appdir / f"{APP_NAME}.desktop"
    desktop.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={DISPLAY_NAME}\n"
        f"Exec={APP_NAME}\n"
        "Icon=wireviz-studio\n"
        "Categories=Development;Electronics;\n"
        "Terminal=false\n",
        encoding="utf-8",
    )

    _make_linux_icon(appdir / "wireviz-studio.png")

    artifact_dir = _artifact_dir(target)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    out_file = artifact_dir / (
        f"wireviz-studio-{_normalized_version(version_text)}-appimage-"
        f"{_platform_tag()}-{_python_tag()}.AppImage"
    )

    _run([appimagetool, str(appdir), str(out_file)])

    # Optional detached signature when gpg key is loaded in CI/local shell.
    if shutil.which("gpg") and os.getenv("GPG_SIGN_APPIMAGE", "").strip() == "1":
        _run(["gpg", "--batch", "--yes", "--armor", "--detach-sign", str(out_file)])

    return out_file


def main() -> int:
    args = _parse_args()
    platform_tag = _platform_tag()

    target_platform_map = {
        "windows-installer": "windows",
        "macos-dmg": "macos",
        "linux-appimage": "linux",
    }
    expected_platform = target_platform_map[args.target]
    if expected_platform != platform_tag:
        raise RuntimeError(
            f"Target '{args.target}' must run on {expected_platform}, current platform is {platform_tag}."
        )

    dirs = _build_dirs(args.target)
    artifact_dir = _artifact_dir(args.target)

    if args.clean:
        _remove_path(dirs["base"])
        _remove_path(artifact_dir)

    print(f"Target         : {args.target}")
    print(f"Platform       : {platform_tag}")
    print(f"Python         : {_python_tag()}")
    print(f"Version        : {_normalized_version(args.version)}")
    print(f"PyInstaller out: {dirs['dist']}")
    print(f"Artifacts out  : {artifact_dir}")

    app_output = _run_pyinstaller(args.target)

    if args.target == "windows-installer":
        artifact = _build_windows_installer(app_output, args.target, args.version)
    elif args.target == "macos-dmg":
        artifact = _build_macos_dmg(app_output, args.target, args.version)
    else:
        artifact = _build_linux_appimage(app_output, args.target, args.version)

    print(f"Created artifact: {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

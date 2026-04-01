"""GraphViz download workflow utilities.

Public API
----------
download_graphviz(install_dir, progress_cb=None)
    Top-level entry: scrape → download → verify → extract (dot-only).

scrape_zip_info(platform, arch) -> (zip_url, sha256_url)
fetch_sha256_digest(sha256_url) -> str
download_file_with_progress(url, dest, progress_cb=None) -> Path
extract_dot_only(zip_path, install_dir) -> None
"""

from __future__ import annotations

import hashlib
import html.parser
import re
import struct
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# Existing helpers (v1)
# ---------------------------------------------------------------------------

def sha256sum(file_path: Path) -> str:
    """Compute SHA256 checksum for a file."""
    digest = hashlib.sha256()
    with file_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, destination: Path) -> Path:
    """Download *url* to *destination* (no progress reporting)."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as resp, destination.open("wb") as out:
        out.write(resp.read())
    return destination


def verify_sha256(file_path: Path, expected_sha256: str) -> bool:
    """Return True when the file's SHA256 matches *expected_sha256*."""
    return sha256sum(file_path).lower() == expected_sha256.lower()


# ---------------------------------------------------------------------------
# v2 — auto-download implementation
# ---------------------------------------------------------------------------

_GRAPHVIZ_DOWNLOAD_PAGE = "https://graphviz.org/download/"

# Executables bundled by GraphViz that are NOT needed to run dot.
# These are filtered out by extract_dot_only() to keep the install small.
_EXTRA_EXECUTABLES = {
    "neato", "fdp", "sfdp", "twopi", "circo", "osage", "patchwork",
    "gv2gml", "gxl2gv", "gvcolor", "gvpack", "gvgen", "gvmap",
    "mm2gv", "acyclic", "ccomps", "gc", "nop", "sccmap", "tred",
    "unflatten", "diffimg", "dijkstra", "edgepaint",
    "dot_static", "lefty", "lneato", "gvedit", "smyrna",
    "cluster", "bcomps", "graphml2gv",
}

def get_latest_version() -> Optional[str]:
    """Scrape graphviz.org/download/ and return the latest version string.

    Returns:
        Version string like "2.49.3" or None if not found.
    """
    try:
        req = urllib.request.Request(
            _GRAPHVIZ_DOWNLOAD_PAGE,
            headers={"User-Agent": "WireViz-Studio/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            page_html = resp.read().decode("utf-8", errors="replace")

        # Collect every version-like token from page text/links and choose the max.
        # Example matches: "graphviz-14.1.4", "Graphviz-12.2.1-win64.zip".
        versions = re.findall(r"graphviz-(\d+\.\d+\.\d+)", page_html, flags=re.IGNORECASE)
        if not versions:
            return None

        def _version_key(version: str) -> tuple[int, int, int]:
            major, minor, patch = version.split(".")
            return int(major), int(minor), int(patch)

        return max(versions, key=_version_key)
    except Exception:  # noqa: BLE001
        return None


class _ZipLinkParser(html.parser.HTMLParser):
    """Collect href values that look like GraphViz ZIP download links."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for attr_name, attr_value in attrs:
            if attr_name == "href" and attr_value and ".zip" in attr_value.lower():
                self.links.append(attr_value)


def _pointer_bits() -> int:
    """Return pointer width in bits (32 or 64)."""
    return struct.calcsize("P") * 8


def scrape_zip_info(os_name: str, arch: int) -> tuple[str, str]:
    """Scrape graphviz.org/download/ and return ``(zip_url, sha256_url)``.

    Args:
        os_name: One of ``"windows"``, ``"linux"``, ``"macos"``.
        arch:    32 or 64.

    Raises:
        NotImplementedError: For macOS (use Homebrew) or Linux (future stub).
        RuntimeError:        When no matching ZIP link is found on the page.
    """
    if os_name in ("darwin", "macos"):
        raise NotImplementedError(
            "Automatic download is not supported on macOS. "
            "Install GraphViz via Homebrew: brew install graphviz"
        )
    if os_name not in ("windows", "win32"):
        raise NotImplementedError(
            f"Automatic download is not yet supported on {os_name}. "
            "Install GraphViz from your distribution's package manager."
        )

    suffix = f"win{arch}.zip"
    with urllib.request.urlopen(_GRAPHVIZ_DOWNLOAD_PAGE) as resp:
        page_html = resp.read().decode("utf-8", errors="replace")

    parser = _ZipLinkParser()
    parser.feed(page_html)

    for link in parser.links:
        if suffix in link.lower():
            zip_url = link if link.startswith("http") else "https://graphviz.org" + link
            return zip_url, zip_url + ".sha256"

    raise RuntimeError(
        f"Could not find a GraphViz {arch}-bit ZIP link on {_GRAPHVIZ_DOWNLOAD_PAGE}. "
        "Please install GraphViz manually."
    )


def fetch_sha256_digest(sha256_url: str) -> str:
    """Fetch a ``.sha256`` file and return the hex digest.

    The file format is ``{64-char hex}  {filename}\\n``.
    """
    with urllib.request.urlopen(sha256_url) as resp:
        content = resp.read().decode("utf-8", errors="replace").strip()
    return content.split()[0]


def download_file_with_progress(
    url: str,
    destination: Path,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> Path:
    """Stream *url* to *destination*, calling *progress_cb(received, total)* per chunk.

    *total* is ``-1`` when the server does not send ``Content-Length``.
    Chunks are 64 KB.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    chunk_size = 64 * 1024
    with urllib.request.urlopen(url) as resp:
        total = int(resp.headers.get("Content-Length", -1))
        received = 0
        with destination.open("wb") as out:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                out.write(chunk)
                received += len(chunk)
                if progress_cb is not None:
                    progress_cb(received, total)
    return destination


def extract_dot_only(zip_path: Path, install_dir: Path) -> None:
    """Unpack only the files required to run ``dot`` from a GraphViz Windows ZIP.

    Keeps:
    - ``bin/dot.exe`` and every ``bin/*.dll``
    - ``lib/graphviz/`` tree (layout-engine plugins)

    Skips all other executables, ``include/``, ``doc/``, and ``share/``.

    The ZIP's top-level ``Graphviz-{VER}-{arch}/`` prefix is stripped so that
    files land directly under *install_dir*.
    """
    install_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            parts = Path(member.filename).parts
            if not parts:
                continue
            # Strip leading version folder (Graphviz-X.Y.Z-win64/)
            rel_parts = parts[1:] if len(parts) > 1 else parts
            if not rel_parts:
                continue

            section = rel_parts[0]  # "bin", "lib", "include", "doc", "share" …
            rel_path = Path(*rel_parts)

            if section == "bin":
                stem = rel_path.stem.lower()
                ext = rel_path.suffix.lower()
                # Keep dot.exe and all DLLs; drop every other executable
                if ext == ".exe" and stem != "dot":
                    continue
                if ext == "" and stem in _EXTRA_EXECUTABLES:
                    # Linux ELF executables have no extension
                    continue
            elif section == "lib":
                # Keep only lib/graphviz/ (layout plugins)
                if len(rel_parts) < 2 or rel_parts[1] != "graphviz":
                    continue
            else:
                # include/, doc/, share/ — skip entirely
                continue

            out_path = install_dir / rel_path
            if member.is_dir():
                out_path.mkdir(parents=True, exist_ok=True)
                continue
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, out_path.open("wb") as dst:
                dst.write(src.read())


def download_graphviz(
    install_dir: Path,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    stage_cb: Optional[Callable[[str], None]] = None,
) -> dict[str, str]:
    """Download and install a minimal GraphViz ``dot`` distribution.

    Steps:
        1. Detect platform + pointer width.
        2. Scrape graphviz.org/download/ for the ZIP and ``.sha256`` URLs.
        3. Stream the ZIP to a temp file, calling *progress_cb* per chunk.
        4. Verify the SHA256 digest.
        5. Extract dot-only subset into *install_dir*.

    Args:
        install_dir:  Target directory (e.g. ``bundled_graphviz/windows/``).
        progress_cb:  Optional ``(received_bytes, total_bytes)`` callback.
        stage_cb:     Optional stage update callback (e.g. "Downloading...").

    Returns:
        Dict with ``"zip_url"`` and ``"expected_digest"`` for verification display.

    Raises:
        NotImplementedError: Unsupported platforms (macOS, Linux).
        RuntimeError:        Download page yields no usable link.
        ValueError:          SHA256 verification fails.
    """
    if stage_cb:
        stage_cb("Fetching release information…")

    os_name = "windows" if sys.platform.startswith("win") else sys.platform
    bits = _pointer_bits()

    zip_url, sha256_url = scrape_zip_info(os_name, bits)

    if stage_cb:
        stage_cb("Verifying integrity…")
    expected_digest = fetch_sha256_digest(sha256_url)

    if stage_cb:
        stage_cb("Downloading…")

    with tempfile.TemporaryDirectory() as tmp:
        zip_name = zip_url.rsplit("/", 1)[-1]
        zip_path = Path(tmp) / zip_name
        download_file_with_progress(zip_url, zip_path, progress_cb)

        if stage_cb:
            stage_cb("Verifying archive…")
        actual_digest = sha256sum(zip_path)
        if actual_digest.lower() != expected_digest.lower():
            raise ValueError(
                f"SHA256 mismatch for {zip_name}. "
                "The downloaded file may be corrupted or tampered with."
            )

        if stage_cb:
            stage_cb("Extracting files…")
        extract_dot_only(zip_path, install_dir)

    return {"zip_url": zip_url, "expected_digest": expected_digest, "actual_digest": actual_digest}

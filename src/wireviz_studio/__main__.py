"""Application entry point for WireViz Studio."""

from wireviz_studio.gui.app import run


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())

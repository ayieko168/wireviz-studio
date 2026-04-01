---
description: "Use when running Python commands in this workspace, including pytest, scripts, package tools, and one-off Python execution. Enforce using the project virtual environment Python executable from venv."
name: "Project Python Venv Execution Rule"
---
# Python Command Environment Rule

- Always run Python commands with the project virtual environment interpreter at `./venv/Scripts/python.exe` (Windows).
- Do not use system Python or plain `python` when a command can run via the project venv interpreter.
- Preferred pattern: `./venv/Scripts/python.exe -m <module_or_tool> [args]`.
- For tests, use: `./venv/Scripts/python.exe -m pytest [args]`.
- If activating instead of direct executable usage, activate the same `venv` at the project root before running commands.
- When installing Python packages for this project, install into this same `venv` environment.

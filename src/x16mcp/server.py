# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""MCP server entry point for the ``x16mcp`` console script.

The module wires up the entry point so the package installs and the script
resolves. The server has no tool surface, so invoking it exits with a message.
"""

from __future__ import annotations


def main() -> None:
    """Run the console entry point, exiting with a message as the server has no tools.

    Raises:
        SystemExit: always, because the server exposes no tools to serve.
    """

    raise SystemExit("x16mcp server has no tools to serve.")

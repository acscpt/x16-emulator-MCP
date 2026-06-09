# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""x16mcp: the MCP server that wraps the x16dbg client harness.

It is the only part of the project that depends on the MCP SDK, installed
through the ``server`` optional extra.
"""

from __future__ import annotations

__version__ = "0.1.3"

__all__ = ["__version__"]

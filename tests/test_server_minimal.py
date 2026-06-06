# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""The MCP server over stdio: it starts, lists tools, and round-trips a session.

This spawns the server as a real subprocess and drives it through an MCP client,
so it covers the JSON-RPC framing and the console entry point that the in-process
tests in test_server.py skip.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402


def _serverParams(emulator: Path, rom: Path) -> StdioServerParameters:
    """Build the stdio parameters that launch the server as a subprocess.

    Args:
        emulator: the emulator binary, passed through the environment.
        rom: the ROM, passed through the environment.

    Returns:
        StdioServerParameters: the parameters for stdio_client.
    """

    # The child process discovers its inputs from the same env vars as Phase 1.
    env = dict(os.environ)
    env["X16EMU_PATH"] = str(emulator)
    env["X16ROM_PATH"] = str(rom)

    params = StdioServerParameters(command=sys.executable, args=["-m", "x16mcp.server"], env=env)
    return params


async def _createListClose(params: StdioServerParameters) -> dict[str, object]:
    """Connect over stdio, list the tools, create a session, then close it.

    Args:
        params: the stdio server parameters.

    Returns:
        dict[str, object]: the tool names seen and the created session id.
    """

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()

            listed = await client.list_tools()
            tool_names = {tool.name for tool in listed.tools}

            created = await client.call_tool("create_session", {})
            session_id = json.loads(created.content[0].text)["session_id"]

            await client.call_tool("close_session", {"session_id": session_id})

    outcome = {"tool_names": tool_names, "session_id": session_id}
    return outcome


def testServerStartsListsAndRoundTrips(emulatorBinary: Path, romPath: Path) -> None:
    """Over stdio the server starts, lists its tools, and a session round-trips.

    Args:
        emulatorBinary: the discovered emulator path fixture.
        romPath: the discovered ROM path fixture.
    """

    params = _serverParams(emulatorBinary, romPath)
    outcome = asyncio.run(_createListClose(params))

    assert "create_session" in outcome["tool_names"]
    assert isinstance(outcome["session_id"], str)
    assert outcome["session_id"]


async def _callBadSession(params: StdioServerParameters) -> dict[str, object]:
    """Call a tool with an unknown session id and return the error outcome.

    Args:
        params: the stdio server parameters.

    Returns:
        dict[str, object]: whether the call errored and the error text.
    """

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            result = await client.call_tool("mode", {"session_id": "no-such-session"})

    outcome = {"is_error": result.isError, "text": result.content[0].text}
    return outcome


def testRaisedExceptionSurfacesAsAToolError(emulatorBinary: Path, romPath: Path) -> None:
    """A raised exception comes back over the wire as a tool error with its message.

    Args:
        emulatorBinary: the discovered emulator path fixture.
        romPath: the discovered ROM path fixture.
    """

    params = _serverParams(emulatorBinary, romPath)
    outcome = asyncio.run(_callBadSession(params))

    assert outcome["is_error"] is True
    assert "no such session" in outcome["text"]

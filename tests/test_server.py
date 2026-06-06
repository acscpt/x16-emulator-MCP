# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""MCP server tools against the live emulator, called in process.

The decorated tool functions stay directly callable, so these exercise the tool
bodies and a real emulator session without the JSON-RPC wire; the wire itself is
covered in test_server_minimal.py.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest

from x16dbg.transport import PROTOCOL_VERSION

pytest.importorskip("mcp")

from x16mcp import server  # noqa: E402


@pytest.fixture
def session(emulatorBinary: Path, romPath: Path) -> Iterator[str]:
    """Create a session and close it when the test finishes.

    Args:
        emulatorBinary: the discovered emulator path fixture.
        romPath: the discovered ROM path fixture.

    Returns:
        Iterator[str]: the created session id.
    """

    created = server.create_session()
    session_id = created["session_id"]

    try:
        yield session_id

    finally:
        # The test may have closed it already; only tear down a live one.
        if session_id in server._sessions:
            server.close_session(session_id)


def testServerListsItsTools() -> None:
    """The server registers the session tools."""

    names = {tool.name for tool in asyncio.run(server.mcp.list_tools())}

    expected = {"create_session", "close_session", "boot_program", "protocol_version", "mode"}
    assert expected <= names


def testCreateSessionReturnsAnId(emulatorBinary: Path, romPath: Path) -> None:
    """create_session boots an emulator and hands back a session id.

    Args:
        emulatorBinary: the discovered emulator path fixture.
        romPath: the discovered ROM path fixture.
    """

    created = server.create_session()

    try:
        assert isinstance(created["session_id"], str)
        assert created["session_id"]

    finally:
        server.close_session(created["session_id"])


def testProtocolVersionAndModeRoundTrip(session: str) -> None:
    """The trivial tools round-trip against a live session.

    Args:
        session: the created session id fixture.
    """

    assert server.protocol_version(session)["protocol_version"] == PROTOCOL_VERSION
    assert server.mode(session)["mode"] in ("stop", "run", "step")


def testCloseSessionRemovesTheSession(emulatorBinary: Path, romPath: Path) -> None:
    """A closed session is acknowledged, gone from the registry, and unresolvable.

    Args:
        emulatorBinary: the discovered emulator path fixture.
        romPath: the discovered ROM path fixture.
    """

    created = server.create_session()
    session_id = created["session_id"]

    acknowledged = server.close_session(session_id)

    assert acknowledged == {"ok": True}
    assert session_id not in server._sessions

    with pytest.raises(KeyError):
        server.protocol_version(session_id)


def testBootProgramRespawnsTheSession(session: str, tmp_path: Path) -> None:
    """boot_program respawns the emulator under the same id and stays usable.

    Args:
        session: the created session id fixture.
        tmp_path: a pytest temporary directory.
    """

    # A minimal .prg (two-byte load address then one NOP); the load itself is
    # paste-driven and not asserted here, only that the respawn succeeds.
    prg = tmp_path / "p.prg"
    prg.write_bytes(bytes([0x00, 0x05, 0xEA]))

    acknowledged = server.boot_program(session, str(prg))

    assert acknowledged == {"ok": True}
    assert server.mode(session)["mode"] in ("stop", "run", "step")


def testCorruptionHuntLoopThroughTools(session: str) -> None:
    """The corruption-hunt loop runs end to end through the MCP tools.

    Args:
        session: the created session id fixture.
    """

    # Arm LDA #$aa ; STA $70 at $0500 via the raw passthrough, then point the PC.
    server.x16db(session, "brk")
    server.x16db(session, "wmm 00 0500 a9 aa 85 70")
    server.x16db(session, "srg pc 0500")

    armed = server.set_watchpoint(session, "w", 0x00, 0x70)
    assert armed["slot"] == 0

    event = server.run_until(session)

    assert event["event"] == "watchpoint"
    assert event["addr"] == 0x70
    assert event["val"] == 0xAA
    assert event["pc"] == 0x0502

    registers = server.read_registers(session)
    assert registers["mode"] in ("c02", "c816")

    dump = server.read_memory(session, 0x00, 0x70, 1)
    assert dump["hex"].startswith("aa")


def testRunUntilReportsABreak(session: str) -> None:
    """run_until reports a tagged break event when the CPU hits a breakpoint.

    Args:
        session: the created session id fixture.
    """

    # Three NOPs at $0500 with a breakpoint two instructions in.
    server.x16db(session, "brk")
    server.x16db(session, "wmm 00 0500 ea ea ea")
    server.x16db(session, "srg pc 0500")
    server.x16db(session, "sbp 00 0502")

    event = server.run_until(session)

    assert event["event"] == "break"
    assert event["reason"] == "BREAKPOINT"
    assert event["addr"] == 0x0502


def testExecutionToolsRoundTrip(session: str) -> None:
    """The execution tools halt, resume, step, and reset a live session.

    Args:
        session: the created session id fixture.
    """

    assert server.brk(session)["event"] == "break"
    assert server.cont(session) == {"ok": True}
    assert server.brk(session)["event"] == "break"
    assert server.step(session)["event"] == "break"
    assert server.reset(session) == {"ok": True}


def testBreakpointToolsRoundTrip(session: str) -> None:
    """The breakpoint tools set, list, toggle, and clear breakpoints.

    Args:
        session: the created session id fixture.
    """

    server.brk(session)
    server.clear_all_breakpoints(session)

    server.set_breakpoint(session, 0x00, 0xC010)
    listed = server.list_breakpoints(session)["breakpoints"]
    assert any(entry["addr"] == 0xC010 for entry in listed)

    server.disable_breakpoint(session, 0x00, 0xC010)
    assert server.list_breakpoints(session)["breakpoints"][0]["enabled"] is False

    server.enable_breakpoint(session, 0x00, 0xC010)
    assert server.list_breakpoints(session)["breakpoints"][0]["enabled"] is True

    server.clear_breakpoint(session, 0x00, 0xC010)
    assert server.list_breakpoints(session)["breakpoints"] == []


def testWatchpointToolsRoundTrip(session: str) -> None:
    """The watchpoint tools arm, list, toggle, and clear watchpoints.

    Args:
        session: the created session id fixture.
    """

    server.brk(session)
    server.clear_watchpoint(session, "*")

    slot = server.set_watchpoint(session, "w", 0x00, 0x70)["slot"]
    listed = server.list_watchpoints(session)["watchpoints"]
    assert listed[0]["id"] == slot
    assert listed[0]["access"] == "w"

    server.disable_watchpoint(session, slot)
    assert server.list_watchpoints(session)["watchpoints"][0]["enabled"] is False

    server.enable_watchpoint(session, slot)
    server.clear_watchpoint(session, "*")
    assert server.list_watchpoints(session)["watchpoints"] == []


def testRegisterToolsRoundTrip(session: str) -> None:
    """set_register writes a register that read_registers reads back.

    Args:
        session: the created session id fixture.
    """

    server.brk(session)
    server.set_register(session, "a", 0x42)

    registers = server.read_registers(session)
    assert registers["a"] == 0x42


def testMemoryToolsRoundTrip(session: str) -> None:
    """The memory tools write, read, fill, and search RAM.

    Args:
        session: the created session id fixture.
    """

    server.brk(session)

    server.write_memory(session, 0x00, 0x0400, [0xDE, 0xAD, 0xBE, 0xEF])
    assert server.read_memory(session, 0x00, 0x0400, 4)["hex"] == "deadbeef"

    server.fill(session, 0x00, 0x0700, 0x5A, 4)
    assert server.read_memory(session, 0x00, 0x0700, 4)["hex"] == "5a5a5a5a"

    matches = server.find(session, 0x00, 0x0000, 0x1000, [0xDE, 0xAD])["matches"]
    assert 0x0400 in matches


def testVramToolsRoundTrip(session: str) -> None:
    """write_vram and read_vram round-trip bytes through VRAM.

    Args:
        session: the created session id fixture.
    """

    server.brk(session)
    server.write_vram(session, 0x00000, [0x11, 0x22, 0x33])

    dump = server.read_vram(session, 0x00000, 3)
    assert dump["start"] == 0x00000
    assert dump["hex"] == "112233"


def testDisassembleToolRoundTrip(session: str) -> None:
    """disassemble decodes bytes into instruction lines.

    Args:
        session: the created session id fixture.
    """

    server.brk(session)
    server.write_memory(session, 0x00, 0x0500, [0xEA, 0xEA])

    lines = server.disassemble(session, 0x00, 0x0500, 2)["lines"]
    assert len(lines) == 2
    assert "nop" in lines[0].lower()


def testInspectionToolsRoundTrip(session: str) -> None:
    """The inspection tools report clock, stack, zero-page, and VERA state.

    Args:
        session: the created session id fixture.
    """

    server.brk(session)

    assert isinstance(server.clocks(session)["clocks"], int)

    entries = server.stack(session, 4)["stack"]
    assert len(entries) == 4
    assert "addr" in entries[0] and "value" in entries[0]

    registers = server.zero_page_registers(session)["registers"]
    assert len(registers) == 16

    vera = server.vera_state(session)
    assert "addr0" in vera and "hscale" in vera


def testSessionToolsRoundTrip(session: str) -> None:
    """The session tools report state and toggle the header lines.

    Args:
        session: the created session id fixture.
    """

    server.brk(session)

    rows = server.state(session)["state"]
    assert any(row.startswith("mode") for row in rows)

    assert server.set_headers(session, False) == {"ok": True}
    assert server.set_header_line(session, "cpu", True) == {"ok": True}


def testScreenshotReturnsAnImage(session: str) -> None:
    """screenshot returns a PNG image block.

    Args:
        session: the created session id fixture.
    """

    image = server.screenshot(session)

    assert image.data[:8] == b"\x89PNG\r\n\x1a\n"


def testX16dbRefusesSessionEndingCommands(session: str) -> None:
    """The passthrough refuses commands that would kill the session.

    Args:
        session: the created session id fixture.
    """

    for ending in ("quit", "qit", "bail"):
        with pytest.raises(ValueError):
            server.x16db(session, ending)

    # The session is still alive and usable after the refusals.
    assert server.mode(session)["mode"] in ("stop", "run", "step")


def testX16dbForceEndsTheSession(session: str) -> None:
    """With force, the passthrough ends the session and the registry drops it.

    Args:
        session: the created session id fixture.
    """

    result = server.x16db(session, "quit", force=True)

    assert result["ended"] is True
    assert session not in server._sessions

    with pytest.raises(KeyError):
        server.mode(session)


def testUnknownSessionRaises() -> None:
    """A tool call naming an unknown session id raises."""

    with pytest.raises(KeyError):
        server.mode("no-such-session")

# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""The transport core, exercised against the live emulator.

Covers the startup handshake and protocol gate, the response split into data,
events, and header, ERR-to-exception, and the warp-speed event race where a
watchpoint hit arrives with the resume's prompt or on the following one.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from x16dbg.transport import PROTOCOL_VERSION, Transport, X16dbgError, X16ProtocolError


@pytest.fixture
def transport(emulatorBinary: Path, romPath: Path) -> Iterator[Transport]:
    """Provide a connected Transport, closed when the test finishes.

    Args:
        emulatorBinary: the discovered emulator path fixture.
        romPath: the discovered ROM path fixture.

    Returns:
        Iterator[Transport]: the single connected transport for the test.
    """

    with Transport(emulatorBinary, romPath) as t:
        yield t


def armRoutine(t: Transport, code: str) -> None:
    """Stop the CPU, write a short routine at $0500, and point the PC at it.

    The break first ensures the PC is set while stopped, since setting it while
    the CPU runs races with instruction fetch.

    Args:
        t: the transport to drive.
        code: the routine as space-separated hex bytes.
    """

    t.command("brk")
    t.command("wmm 00 0500 " + code)
    t.command("srg pc 0500")


def testHandshakeReportsProtocolVersion(transport: Transport) -> None:
    """The handshake records the protocol version it gated on.

    Args:
        transport: the connected transport fixture.
    """

    assert transport.proto_version == PROTOCOL_VERSION


def testProtocolMismatchRefuses(emulatorBinary: Path, romPath: Path) -> None:
    """A required version the emulator does not report raises and closes cleanly.

    Args:
        emulatorBinary: the discovered emulator path fixture.
        romPath: the discovered ROM path fixture.
    """

    with pytest.raises(X16ProtocolError):
        Transport(emulatorBinary, romPath, require_proto=999)


def testBrkEmitsUserBreak(transport: Transport) -> None:
    """A brk command stops the CPU and emits a USER break event.

    Args:
        transport: the connected transport fixture.
    """

    response = transport.command("brk")

    assert any(event.startswith("* BRK USER ") for event in response.events)


def testMemoryRoundTrips(transport: Transport) -> None:
    """Bytes written with wmm read back through mem as data, not header.

    Args:
        transport: the connected transport fixture.
    """

    transport.command("wmm 00 0400 de ad be ef")
    response = transport.command("mem 00 0400 04")

    assert response.data[0].startswith("0400: de ad be ef")


def testUnknownCommandRaisesWithMessage(transport: Transport) -> None:
    """An unrecognised command turns the ERR reply into an exception.

    Args:
        transport: the connected transport fixture.
    """

    with pytest.raises(X16dbgError) as info:
        transport.command("notacommand")

    assert "ERR" in str(info.value)


def testHeaderSeparatedFromData(transport: Transport) -> None:
    """The status header is split out from a command's data lines.

    Args:
        transport: the connected transport fixture.
    """

    transport.command("mod")

    assert len(transport.last_header) >= 3
    assert transport.last_header[0].startswith("1: [")


def testWarpEventRaceCollectsWatchpoint(transport: Transport) -> None:
    """A write watchpoint hit is collected whether it lands with the resume or after.

    Args:
        transport: the connected transport fixture.
    """

    # LDA #$aa ; STA $70 -- the store at $0502 writes the watched location.
    armRoutine(transport, "a9 aa 85 70")
    transport.command("swp 00 0070")

    events = transport.resumeCollectingEvents("cnt", until_prefix="* WP")

    assert any(e.startswith("* WP 0 w 00:0070=aa") and "pc=00:0502" in e for e in events)


def testBuildArgsAssemblesLaunchOptions() -> None:
    """The launch argv reflects the prg, load address, run, startup-bp, and warp options.

    A pure check of the command-line construction, so it needs no emulator. The
    emulator loads a -prg by typing LOAD at the BASIC prompt once it boots, so a
    live load is timing-dependent; the argv is what the harness actually owns.
    """

    plain = Transport._buildArgs("x16emu", "rom.bin", None, None, False, None, True, None)
    assert plain == ["x16emu", "-rom", "rom.bin", "-debugstdio", "-warp"]

    # A PRG with a load-address override and autostart, a startup breakpoint, no warp.
    full = Transport._buildArgs("x16emu", "rom.bin", "app.prg", 0x0801, True, 0xC000, False, None)
    assert full == [
        "x16emu",
        "-rom",
        "rom.bin",
        "-prg",
        "app.prg,801",
        "-run",
        "-debugstdio",
        "c000",
    ]


def testBuildArgsAddsFsrootWhenSet() -> None:
    """A configured fsroot becomes a -fsroot argument, and is omitted otherwise.

    The flag rides just after -rom so it reads as machine setup, and it appears
    only when a root is given; with none the argv is byte-for-byte the default.
    """

    with_root = Transport._buildArgs("x16emu", "rom.bin", None, None, False, None, True, "/srv/x16")
    assert with_root == ["x16emu", "-rom", "rom.bin", "-fsroot", "/srv/x16", "-debugstdio", "-warp"]

    # Omitted leaves no trace of the flag in the argv.
    without = Transport._buildArgs("x16emu", "rom.bin", None, None, False, None, True, None)
    assert "-fsroot" not in without


def testCommandAfterProcessDeathRaises(transport: Transport) -> None:
    """A command sent after the emulator has died raises rather than hanging.

    Args:
        transport: the connected transport fixture.
    """

    transport.proc.kill()
    transport.proc.wait()

    # The send hits a closed pipe or the read hits EOF; either surfaces as an
    # exception instead of blocking on a prompt that will never come.
    with pytest.raises((EOFError, OSError, X16dbgError)):
        transport.command("ver")

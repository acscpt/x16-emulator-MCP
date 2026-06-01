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

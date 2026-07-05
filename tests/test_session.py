# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Session commands against the live emulator.

Covers the machine mode, the state snapshot rows, and header control, the last
checked through the header lines the transport records.
"""

from __future__ import annotations

from pathlib import Path

from x16dbg.client import Client


def testSessionLaunchesWithAFilesystemRoot(
    emulatorBinary: Path, romPath: Path, tmp_path: Path
) -> None:
    """A session boots with -fsroot pointed at a host directory.

    Proves the flag the harness emits is accepted by the emulator and the
    session comes up cleanly; device 8 then serves that directory to a booted
    program. The file inputs come from the discovery fixtures, so the test skips
    cleanly when they are absent.

    Args:
        emulatorBinary: the discovered emulator path fixture.
        romPath: the discovered ROM path fixture.
        tmp_path: pytest temporary directory served as the filesystem root.
    """

    with Client.launch(emulatorBinary, romPath, fsroot=tmp_path) as connected:
        # A reported protocol version means the startup handshake completed, so
        # the emulator accepted the extra -fsroot argument and booted.
        assert connected.protocolVersion is not None
        assert connected.mode() in ("stop", "run")


def testModeReflectsStopAndRun(client: Client) -> None:
    """The mode reports stop while halted and run after a resume.

    Args:
        client: the connected client fixture.
    """

    client.brk()
    assert client.mode() == "stop"

    client.cont()
    assert client.mode() == "run"


def testStateListsLabeledRows(client: Client) -> None:
    """The state snapshot includes the mode and CPU program counter rows.

    Args:
        client: the connected client fixture.
    """

    client.brk()

    rows = client.state()

    assert any(row.startswith("mode") for row in rows)
    assert any(row.startswith("regs.pc") for row in rows)


def testSetHeadersSuppressesAndRestores(client: Client) -> None:
    """Turning headers off clears the recorded header, and on restores it.

    Args:
        client: the connected client fixture.
    """

    client.brk()

    client.setHeaders(False)
    client.mode()
    assert client.transport.last_header == []

    client.setHeaders(True)
    client.mode()
    assert client.transport.last_header != []


def testSetHeaderLineShowsOneLine(client: Client) -> None:
    """Enabling a single header line emits just that line.

    Args:
        client: the connected client fixture.
    """

    client.brk()

    client.setHeaders(False)
    client.setHeaderLine("cpu", True)
    client.mode()

    assert len(client.transport.last_header) == 1

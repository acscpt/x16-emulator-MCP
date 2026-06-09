# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Memory commands against the live emulator.

Covers writing bytes and reading them back, filling a range, and searching for
a pattern, using low RAM so no I/O side effects come into play.
"""

from __future__ import annotations

from x16dbg.client import Client


def testWriteThenReadRoundTrips(client: Client) -> None:
    """Bytes written to RAM read back unchanged through a typed dump.

    Args:
        client: the connected client fixture.
    """

    client.brk()

    client.writeMemory(0x00, 0x0400, [0xDE, 0xAD, 0xBE, 0xEF])
    dump = client.readMemory(0x00, 0x0400, 4)

    assert dump.data == b"\xde\xad\xbe\xef"


def testWriteLongerThanTheWmmCapRoundTrips(client: Client) -> None:
    """A write past the wmm 14-byte line cap is chunked, not silently truncated.

    Args:
        client: the connected client fixture.
    """

    client.brk()

    # Forty distinct bytes span three wmm chunks; clear the range first so a
    # short write cannot pass by leaving stale matching bytes behind.
    values = [(i + 1) & 0xFF for i in range(40)]
    client.fill(0x00, 0x0400, 0x00, 64)
    client.writeMemory(0x00, 0x0400, values)
    dump = client.readMemory(0x00, 0x0400, 40)

    assert dump.data == bytes(values)


def testFillRepeatsTheValue(client: Client) -> None:
    """Fill writes the same byte across the whole range.

    Args:
        client: the connected client fixture.
    """

    client.brk()

    client.fill(0x00, 0x0700, 0x5A, 8)
    dump = client.readMemory(0x00, 0x0700, 8)

    assert dump.data == b"\x5a" * 8


def testFindLocatesPattern(client: Client) -> None:
    """A pattern written into the range is found at its address.

    Args:
        client: the connected client fixture.
    """

    client.brk()

    client.writeMemory(0x00, 0x0600, [0xDE, 0xAD])
    matches = client.find(0x00, 0x0500, 0x0200, [0xDE, 0xAD])

    assert 0x0600 in matches


def testFindReturnsEmptyWhenAbsent(client: Client) -> None:
    """Searching a cleared range for an absent pattern returns no matches.

    Args:
        client: the connected client fixture.
    """

    client.brk()

    client.fill(0x00, 0x0500, 0x00, 0x10)
    matches = client.find(0x00, 0x0500, 0x10, [0xFE, 0xED])

    assert matches == ()


def testHiramReadWriteHonourTheBankArgument(client: Client) -> None:
    """A HiRAM read or write targets the named bank, not the live RAM bank.

    Needs an emulator that resolves the explicit bank for the $A000-$BFFF
    window; on an older build both banks read back the live bank's byte.

    Args:
        client: the connected client fixture.
    """

    client.brk()

    # Distinct markers in two banks at the same HiRAM address; each read must
    # return its own bank's byte, whichever bank the CPU has selected.
    client.writeMemory(0x01, 0xA100, [0x11])
    client.writeMemory(0x02, 0xA100, [0x22])

    assert client.readMemory(0x01, 0xA100, 1).data == b"\x11"
    assert client.readMemory(0x02, 0xA100, 1).data == b"\x22"

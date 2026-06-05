# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""VRAM commands against the live emulator.

Covers writing bytes to VRAM and reading them back, confirming the 17-bit
address space round-trips through the shared dump model.
"""

from __future__ import annotations

from x16dbg.client import Client


def testWriteThenReadVramRoundTrips(client: Client) -> None:
    """Bytes written to VRAM read back unchanged through a typed dump.

    Args:
        client: the connected client fixture.
    """

    client.brk()

    client.writeVram(0x00000, [0xDE, 0xAD, 0xBE, 0xEF])
    dump = client.readVram(0x00000, 4)

    assert dump.start == 0x00000
    assert dump.data == b"\xde\xad\xbe\xef"


def testReadVramHonoursAddress(client: Client) -> None:
    """A read above the 16-bit boundary keeps its 17-bit start address.

    Args:
        client: the connected client fixture.
    """

    client.brk()

    client.writeVram(0x10000, [0x11, 0x22])
    dump = client.readVram(0x10000, 2)

    assert dump.start == 0x10000
    assert dump.data == b"\x11\x22"

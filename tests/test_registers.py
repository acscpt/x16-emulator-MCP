# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Register commands against the live emulator.

Covers reading the register snapshot and setting individual registers, checking
each value set reads back through the typed snapshot.
"""

from __future__ import annotations

import pytest

from x16dbg.client import Client
from x16dbg.transport import X16dbgError


def testReadRegistersReturnsSnapshot(client: Client) -> None:
    """Reading registers returns a snapshot naming the CPU mode.

    Args:
        client: the connected client fixture.
    """

    client.brk()

    registers = client.readRegisters()

    assert registers.mode in ("c02", "c816")


def testSetRegisterWritesWordAndByte(client: Client) -> None:
    """A set register reads back through the snapshot, for a word and a byte.

    Args:
        client: the connected client fixture.
    """

    client.brk()

    client.setRegister("pc", 0x0500)
    client.setRegister("a", 0x42)

    registers = client.readRegisters()
    assert registers.pc == 0x0500
    assert registers.a == 0x42


def testSetUnknownRegisterRaises(client: Client) -> None:
    """Setting a register the emulator does not know raises rather than passing.

    Args:
        client: the connected client fixture.
    """

    client.brk()

    with pytest.raises(X16dbgError):
        client.setRegister("nope", 0x00)

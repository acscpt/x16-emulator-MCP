# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""The vertical slice: the memory-corruption hunt loop end to end.

This proves the whole Phase 1 column in one path: launch the client, arm a
write watchpoint on a zero-page byte, run, and read the culprit program counter
and the surrounding state back as typed results. It mirrors the emulator smoke
test's arm-and-resume pattern.
"""

from __future__ import annotations

from x16dbg.client import Client
from x16dbg.models import AccessType, WatchHit


def armCorruptingRoutine(c: Client) -> None:
    """Stop the CPU and install LDA #$aa ; STA $70 at $0500, pointed to by PC.

    The routine writes the watched zero-page byte $70 from the store at $0502,
    so the watchpoint reports that program counter as the culprit.

    Args:
        c: the client to set up.
    """

    c.transport.command("brk")
    c.transport.command("wmm 00 0500 a9 aa 85 70")
    c.transport.command("srg pc 0500")


def testCorruptionHuntLoop(client: Client) -> None:
    """A write watchpoint catches the store and names the writing instruction.

    Args:
        client: the connected client fixture.
    """

    armCorruptingRoutine(client)

    slot = client.setWatchpoint(AccessType.WRITE, 0x00, 0x70)
    assert slot == 0

    event = client.runUntil()

    assert isinstance(event, WatchHit)
    assert event.access is AccessType.WRITE
    assert event.addr == 0x70
    assert event.val == 0xAA
    assert event.pc == 0x0502
    assert client.last_event is event

    # The context around the hit is available as typed results.
    registers = client.readRegisters()
    assert registers.mode in ("c02", "c816")

    dump = client.readMemory(0x00, 0x70, 1)
    assert dump.data[0] == 0xAA

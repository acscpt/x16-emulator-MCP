# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Watchpoint commands against the live emulator.

Covers arming a byte or a range, listing the armed set as typed results,
attaching a condition, disabling and re-enabling, and clearing. The end-to-end
resume loop a watchpoint drives lives in test_slice.py.
"""

from __future__ import annotations

import pytest

from x16dbg.client import Client
from x16dbg.models import AccessType, BreakEvent, BreakReason, WatchHit
from x16dbg.transport import X16dbgError


def testSetListAndClearWatchpoint(client: Client) -> None:
    """An armed watchpoint lists as a typed result and is gone after a clear.

    Args:
        client: the connected client fixture.
    """

    client.brk()
    client.clearWatchpoint("*")

    slot = client.setWatchpoint(AccessType.WRITE, 0x00, 0x70)
    listed = client.listWatchpoints()

    assert len(listed) == 1
    armed = listed[0]
    assert armed.id == slot
    assert armed.access is AccessType.WRITE
    assert armed.bank == 0x00
    assert armed.addr == 0x70
    assert armed.end is None
    assert armed.hits == 0
    assert armed.enabled is True
    assert armed.condition is None

    client.clearWatchpoint(slot)
    assert client.listWatchpoints() == ()


def testRangeWatchpointListsItsEnd(client: Client) -> None:
    """A range watchpoint reports its inclusive end and access type.

    Args:
        client: the connected client fixture.
    """

    client.brk()
    client.clearWatchpoint("*")

    client.setWatchpoint(AccessType.READWRITE, 0x00, 0x80, end=0x8F)
    (armed,) = client.listWatchpoints()

    assert armed.access is AccessType.READWRITE
    assert armed.addr == 0x80
    assert armed.end == 0x8F


def testConditionalWatchpointListsCondition(client: Client) -> None:
    """A watchpoint condition is accepted and shown verbatim on the list.

    Args:
        client: the connected client fixture.
    """

    client.brk()
    client.clearWatchpoint("*")

    client.setWatchpoint(AccessType.WRITE, 0x00, 0x70, condition="val == $aa")
    (armed,) = client.listWatchpoints()

    assert armed.condition == "val == $aa"


def testDisableThenEnableTogglesTheFlag(client: Client) -> None:
    """Disabling a watchpoint flips its enabled flag, and enabling restores it.

    Args:
        client: the connected client fixture.
    """

    client.brk()
    client.clearWatchpoint("*")

    slot = client.setWatchpoint(AccessType.WRITE, 0x00, 0x70)

    client.disableWatchpoint(slot)
    assert client.listWatchpoints()[0].enabled is False

    client.enableWatchpoint(slot)
    assert client.listWatchpoints()[0].enabled is True


def testDisabledWatchpointDoesNotFire(client: Client) -> None:
    """A disabled watchpoint lets the watched write pass; the CPU stops elsewhere.

    Args:
        client: the connected client fixture.
    """

    # Routine: LDA #$aa ; STA $70 ; STP, so the CPU halts cleanly just past the
    # watched write rather than running on into uninitialised memory.
    client.brk()
    client.clearWatchpoint("*")
    client.transport.command("wmm 00 0500 a9 aa 85 70 db")
    client.transport.command("srg pc 0500")

    slot = client.setWatchpoint(AccessType.WRITE, 0x00, 0x70)
    client.disableWatchpoint(slot)

    # The store happens, but the muted watchpoint does not stop the CPU: it runs
    # through to the STP and breaks there, its hit count untouched.
    event = client.runUntil()

    assert isinstance(event, BreakEvent)
    assert event.reason is BreakReason.STP
    assert client.listWatchpoints()[0].hits == 0


def testEnableMissingWatchpointRaises(client: Client) -> None:
    """Toggling a slot that holds no watchpoint raises rather than passing.

    Args:
        client: the connected client fixture.
    """

    client.brk()
    client.clearWatchpoint("*")

    with pytest.raises(X16dbgError):
        client.enableWatchpoint(0)


def testReadWatchpointFires(client: Client) -> None:
    """A read watchpoint fires on a load, reporting access r and the byte read.

    Args:
        client: the connected client fixture.
    """

    # LDA $0550 ; STP, with a known byte parked at the watched address.
    client.brk()
    client.clearWatchpoint("*")
    client.transport.command("wmm 00 0500 ad 50 05 db")
    client.transport.command("wmm 00 0550 cc")
    client.setRegister("pc", 0x0500)

    slot = client.setWatchpoint(AccessType.READ, 0x00, 0x0550)
    event = client.runUntil()

    assert isinstance(event, WatchHit)
    assert event.access is AccessType.READ
    assert event.addr == 0x0550
    assert event.val == 0xCC
    assert event.pc == 0x0500
    assert client.listWatchpoints()[slot].hits == 1


def testConditionalWatchpointFiresWhenTrue(client: Client) -> None:
    """A watchpoint whose condition holds fires on the matching write.

    Args:
        client: the connected client fixture.
    """

    client.brk()
    client.clearWatchpoint("*")
    client.transport.command("wmm 00 0500 a9 aa 85 70")  # LDA #$aa ; STA $70
    client.setRegister("pc", 0x0500)

    client.setWatchpoint(AccessType.WRITE, 0x00, 0x70, condition="val == $aa")
    event = client.runUntil()

    assert isinstance(event, WatchHit)
    assert event.val == 0xAA
    assert event.pc == 0x0502


def testConditionalWatchpointDoesNotFireWhenFalse(client: Client) -> None:
    """A watchpoint whose condition is false lets the write pass to the STP.

    Args:
        client: the connected client fixture.
    """

    client.brk()
    client.clearWatchpoint("*")
    client.transport.command("wmm 00 0500 a9 aa 85 70 db")  # LDA #$aa ; STA $70 ; STP
    client.setRegister("pc", 0x0500)

    client.setWatchpoint(AccessType.WRITE, 0x00, 0x70, condition="val == $bb")
    event = client.runUntil()

    assert isinstance(event, BreakEvent)
    assert event.reason is BreakReason.STP
    assert client.listWatchpoints()[0].hits == 0

# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Breakpoint commands against the live emulator.

Covers arming, listing, and clearing breakpoints by location, and the headline
behaviour: a breakpoint stops the running CPU when execution reaches it.
"""

from __future__ import annotations

import pytest

from x16dbg.client import Client
from x16dbg.models import BreakEvent, BreakReason
from x16dbg.transport import X16dbgError


def testSetListAndClearBreakpoints(client: Client) -> None:
    """Armed breakpoints list in order, and clearing removes one or all.

    Args:
        client: the connected client fixture.
    """

    client.clearAllBreakpoints()

    client.setBreakpoint(0x00, 0xC010)
    client.setBreakpoint(0x00, 0xC04F, condition="a == $ff")

    listed = client.listBreakpoints()

    assert len(listed) == 2
    assert (listed[0].bank, listed[0].addr, listed[0].condition) == (0x00, 0xC010, None)
    assert (listed[1].addr, listed[1].condition) == (0xC04F, "a == $ff")

    client.clearBreakpoint(0x00, 0xC010)
    remaining = client.listBreakpoints()

    assert len(remaining) == 1
    assert remaining[0].addr == 0xC04F

    client.clearAllBreakpoints()
    assert client.listBreakpoints() == ()


def testClearMissingBreakpointRaises(client: Client) -> None:
    """Clearing a location with no breakpoint raises rather than passing.

    Args:
        client: the connected client fixture.
    """

    client.clearAllBreakpoints()

    with pytest.raises(X16dbgError):
        client.clearBreakpoint(0x00, 0xC010)


def testBreakpointStopsCpuAtAddress(client: Client) -> None:
    """A breakpoint stops the running CPU when execution reaches its address.

    Args:
        client: the connected client fixture.
    """

    # Install three NOPs at $0500 and point the PC at the first.
    client.brk()
    client.transport.command("wmm 00 0500 ea ea ea")
    client.transport.command("srg pc 0500")
    client.clearAllBreakpoints()

    # Break two instructions ahead; running should stop on reaching it.
    client.setBreakpoint(0x00, 0x0502)
    event = client.runUntil()

    assert isinstance(event, BreakEvent)
    assert event.reason is BreakReason.BREAKPOINT
    assert event.addr == 0x0502


def testDisableThenEnableTogglesTheFlag(client: Client) -> None:
    """Disabling a breakpoint flips its enabled flag, and enabling restores it.

    Args:
        client: the connected client fixture.
    """

    client.brk()
    client.clearAllBreakpoints()
    client.setBreakpoint(0x00, 0xC010)

    client.disableBreakpoint(0x00, 0xC010)
    assert client.listBreakpoints()[0].enabled is False

    client.enableBreakpoint(0x00, 0xC010)
    assert client.listBreakpoints()[0].enabled is True


def testDisabledBreakpointDoesNotFire(client: Client) -> None:
    """A disabled breakpoint is passed over; the CPU stops at the STP instead.

    Args:
        client: the connected client fixture.
    """

    # Routine: NOP ; NOP ; STP, so the CPU halts cleanly past the breakpoint.
    client.brk()
    client.clearAllBreakpoints()
    client.transport.command("wmm 00 0500 ea ea db")
    client.transport.command("srg pc 0500")

    client.setBreakpoint(0x00, 0x0501)
    client.disableBreakpoint(0x00, 0x0501)

    event = client.runUntil()

    assert isinstance(event, BreakEvent)
    assert event.reason is BreakReason.STP


def testBankedBreakpointStoresItsBank(client: Client) -> None:
    """A banked-window breakpoint records the X16 bank it was set in.

    Above $A000 a breakpoint's identity includes the X16 bank, and it fires only
    while that bank is the one mapped there. This asserts the stored bank through
    st rather than a free-run hit: a live banked-fire test is non-deterministic
    because the KERNAL remaps the window's bank as it runs. It guards the fork
    regression where a banked breakpoint stored bank -1 and so never fired.

    Args:
        client: the connected client fixture.
    """

    client.brk()
    client.clearAllBreakpoints()

    client.setBreakpoint(0x02, 0xA100)

    # st reports each breakpoint as "bp  <k-bank>:<addr>  x16bank=<n>"; the
    # banked address must record bank 2, the value the bug failed to store.
    bp_lines = [row for row in client.state() if row.lstrip().startswith("bp ")]

    assert any("a100" in line and "x16bank=2" in line for line in bp_lines)


def testReaddingBreakpointReplacesItsCondition(client: Client) -> None:
    """Re-issuing a breakpoint updates its condition in place, then clears it.

    Args:
        client: the connected client fixture.
    """

    client.brk()
    client.clearAllBreakpoints()

    client.setBreakpoint(0x00, 0xC010, condition="a == $ff")
    assert client.listBreakpoints()[0].condition == "a == $ff"

    client.setBreakpoint(0x00, 0xC010, condition="x == $01")
    updated = client.listBreakpoints()
    assert len(updated) == 1
    assert updated[0].condition == "x == $01"

    client.setBreakpoint(0x00, 0xC010)
    cleared = client.listBreakpoints()
    assert len(cleared) == 1
    assert cleared[0].condition is None


def testConditionalBreakpointFiresWhenTrue(client: Client) -> None:
    """A breakpoint whose condition holds stops the CPU at its address.

    Args:
        client: the connected client fixture.
    """

    client.brk()
    client.clearAllBreakpoints()
    client.transport.command("wmm 00 0500 a9 aa 85 70")  # LDA #$aa ; STA $70
    client.setRegister("pc", 0x0500)

    client.setBreakpoint(0x00, 0x0502, condition="a == $aa")
    event = client.runUntil()

    assert isinstance(event, BreakEvent)
    assert event.reason is BreakReason.BREAKPOINT
    assert event.addr == 0x0502


def testConditionalBreakpointDoesNotFireWhenFalse(client: Client) -> None:
    """A breakpoint whose condition is false is passed over; the CPU hits STP.

    Args:
        client: the connected client fixture.
    """

    client.brk()
    client.clearAllBreakpoints()
    client.transport.command("wmm 00 0500 a9 aa 85 70 db")  # LDA #$aa ; STA $70 ; STP
    client.setRegister("pc", 0x0500)

    client.setBreakpoint(0x00, 0x0502, condition="a == $05")
    event = client.runUntil()

    assert isinstance(event, BreakEvent)
    assert event.reason is BreakReason.STP

# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Execution-control commands against the live emulator.

Covers forcing a break, single-stepping, stepping over, and reset, using a
short NOP routine so the steps land on known addresses.
"""

from __future__ import annotations

from x16dbg.client import Client
from x16dbg.models import BreakEvent, BreakReason


def armNops(c: Client) -> None:
    """Stop the CPU and install three NOPs at $0500, pointed to by PC.

    Args:
        c: the client to set up.
    """

    c.brk()
    c.transport.command("wmm 00 0500 ea ea ea")
    c.transport.command("srg pc 0500")


def testBrkForcesUserBreak(client: Client) -> None:
    """brk stops the running CPU and reports a USER break.

    Args:
        client: the connected client fixture.
    """

    event = client.brk()

    assert isinstance(event, BreakEvent)
    assert event.reason is BreakReason.USER
    assert client.last_event is event


def testStepAdvancesOneInstruction(client: Client) -> None:
    """A single step runs one NOP and lands on the next address.

    Args:
        client: the connected client fixture.
    """

    armNops(client)

    event = client.step()

    assert isinstance(event, BreakEvent)
    assert event.reason is BreakReason.STEP
    assert event.addr == 0x0501


def testStepOverNonCallStepsOne(client: Client) -> None:
    """Stepping over a non-call instruction behaves like a single step.

    Args:
        client: the connected client fixture.
    """

    armNops(client)

    event = client.stepOver()

    assert isinstance(event, BreakEvent)
    assert event.reason is BreakReason.STEP
    assert event.addr == 0x0501


def testResetStaysStopped(client: Client) -> None:
    """Reset leaves the machine in STOP rather than resuming it.

    Args:
        client: the connected client fixture.
    """

    client.brk()
    client.reset()

    mode = client.transport.command("mod").data[0]
    assert "mode=stop" in mode


def testStepOverCallCompletesAtReturn(client: Client) -> None:
    """Stepping over a JSR runs the call and stops at the return address.

    Args:
        client: the connected client fixture.
    """

    # JSR $0510 at $0500, RTS at $0510; stepping over lands on $0503, the
    # instruction after the three-byte call. The completing event arrives
    # asynchronously after the * RES, which stepOver collects across.
    client.brk()
    client.transport.command("wmm 00 0500 20 10 05")
    client.transport.command("wmm 00 0510 60")
    client.setRegister("pc", 0x0500)

    event = client.stepOver()

    assert isinstance(event, BreakEvent)
    assert event.reason is BreakReason.STEP
    assert event.addr == 0x0503

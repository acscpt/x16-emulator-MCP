# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Inspection commands against the live emulator.

Covers the clock, the stack top, the zero-page R0..R15 pseudo-registers, and a
VERA state snapshot, using known writes where a value can be pinned.
"""

from __future__ import annotations

import time

from x16dbg.client import Client


def testClocksReturnsCount(client: Client) -> None:
    """The clock reports a non-negative cycle count.

    Args:
        client: the connected client fixture.
    """

    client.brk()

    count = client.clocks()

    assert isinstance(count, int)
    assert count >= 0


def testStackReadsEntriesFromSp(client: Client) -> None:
    """Stack entries read upward from one past the stack pointer.

    Args:
        client: the connected client fixture.
    """

    client.brk()
    client.setRegister("sp", 0x01FB)
    client.transport.command("wmm 00 01fc aa bb cc")

    entries = client.stack(3)

    assert len(entries) == 3
    assert entries[0].addr == 0x01FC
    assert entries[0].value == 0xAA
    assert entries[2].value == 0xCC


def testZeroPageRegistersReadsSixteen(client: Client) -> None:
    """The zero-page registers come back as sixteen words, R0 first.

    Args:
        client: the connected client fixture.
    """

    client.brk()
    # R0 is the little-endian word at the direct page + 2/3 ($02/$03 on 65C02).
    client.transport.command("wmm 00 0002 34 12")

    registers = client.zeroPageRegisters()

    assert len(registers) == 16
    assert registers[0] == 0x1234


def testVeraStateReturnsSnapshot(client: Client) -> None:
    """A VERA snapshot parses its fields into integers.

    Args:
        client: the connected client fixture.
    """

    client.brk()

    state = client.veraState()

    assert isinstance(state.addr0, int)
    assert isinstance(state.hscale, int)


def testVeraTimingAdvancesWhileTheCpuRuns(client: Client) -> None:
    """VERA keeps ticking under -debugstdio, so VBL-paced programs make progress.

    Regression for the headless-VERA freeze: -debugstdio is windowless, but VERA
    must still advance its frame timing (the VBL flag, raster, ISR) or any program
    that polls $9F27 bit 0 spins forever. Running the CPU in short bursts and
    sampling VERA's video register must show it change; a frozen VERA reports one
    constant value at every stop. Needs an emulator with the headless-VERA fix.

    Args:
        client: the connected client fixture.
    """

    seen = set()

    # Run the CPU in short bursts, sampling VERA's video register at each stop.
    # Its current-field bit toggles every frame, so a live VERA yields more than
    # one value across the stops while a frozen one stays put. Poll until it
    # changes rather than fixing the burst count, so a loaded CI runner that
    # ticks VERA slowly gets more attempts instead of flaking; a frozen VERA
    # never changes and still fails once the attempts run out.
    for _ in range(40):
        client.cont()
        time.sleep(0.05)
        client.brk()
        seen.add(client.veraState().video)

        if len(seen) > 1:
            break

    assert len(seen) > 1

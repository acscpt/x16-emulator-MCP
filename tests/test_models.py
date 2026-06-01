# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Parsing of the typed result models from their wire forms.

These are pure parser tests over sample lines captured from the live emulator,
so they need no running emulator.
"""

from __future__ import annotations

import pytest

from x16dbg.models import (
    AccessType,
    BreakEvent,
    BreakReason,
    MemoryDump,
    MemoryRow,
    Registers,
    WatchHit,
)
from x16dbg.transport import X16dbgError


def testWatchHitParsesWriteEvent() -> None:
    """A write watchpoint line parses into its fields."""

    hit = WatchHit.parse("* WP 0 w 00:0070=aa pc=00:0502")

    assert hit.id == 0
    assert hit.access is AccessType.WRITE
    assert hit.addr == 0x70
    assert hit.val == 0xAA
    assert hit.pc == 0x0502


def testWatchHitParsesReadEvent() -> None:
    """A read watchpoint line parses with the read access type."""

    hit = WatchHit.parse("* WP 1 r 00:0550=cc pc=00:0500")

    assert hit.access is AccessType.READ
    assert hit.val == 0xCC
    assert hit.pc == 0x0500


def testWatchHitRejectsNonWatchpointLine() -> None:
    """A line that is not a watchpoint event raises."""

    with pytest.raises(X16dbgError):
        WatchHit.parse("* RES")


def testBreakEventParsesBreakpoint() -> None:
    """A breakpoint break parses its reason and address."""

    event = BreakEvent.parse("* BRK BREAKPOINT 00 080d")

    assert event.reason is BreakReason.BREAKPOINT
    assert event.addr == 0x080D


def testBreakEventParsesStpReason() -> None:
    """A STP break parses the STP reason."""

    event = BreakEvent.parse("* BRK STP 00 0203")

    assert event.reason is BreakReason.STP
    assert event.addr == 0x0203


def testBreakEventRejectsUnknownReason() -> None:
    """An unrecognised break reason raises."""

    with pytest.raises(X16dbgError):
        BreakEvent.parse("* BRK NOPE 00 0000")


def testRegistersParseRealDump() -> None:
    """The reg dump line parses into the register snapshot."""

    line = (
        "mode=c02 pc=f8c3 a=01 b=00 c=0000 x=0008 y=0000 "
        "sp=01fd p=35 k=00 db=00 dp=0000 e=1 ram=00 rom=00"
    )

    regs = Registers.parse(line)

    assert regs.mode == "c02"
    assert regs.pc == 0xF8C3
    assert regs.a == 0x01
    assert regs.sp == 0x01FD
    assert regs.e == 1
    assert regs.ram == 0


def testRegistersMissingFieldRaises() -> None:
    """A reg dump missing a field raises rather than guessing."""

    with pytest.raises(X16dbgError):
        Registers.parse("mode=c02 pc=c000")


def testMemoryRowParsesAddressAndBytes() -> None:
    """A dump row parses its address and sixteen bytes."""

    row = MemoryRow.parse("0400: de ad be ef 01 02 03 04 05 06 07 08 09 0a f1 99  ................")

    assert row.addr == 0x0400
    assert len(row.data) == 16
    assert row.data[0] == 0xDE
    assert row.data[3] == 0xEF


def testMemoryDumpConcatenatesRows() -> None:
    """A multi-row dump exposes its start address and joined bytes."""

    lines = [
        "0400: de ad be ef 01 02 03 04 05 06 07 08 09 0a f1 99  ................",
        "0410: b8 1d 8b 1e af 35 e6 f9 23 81 31 28 96 73 33 e0  .....5..#.1(.s3.",
    ]

    dump = MemoryDump.parse(lines)

    assert dump.start == 0x0400
    assert len(dump.data) == 32
    assert dump.data[16] == 0xB8


def testMemoryRowRejectsNonRow() -> None:
    """A line that is not a dump row raises."""

    with pytest.raises(X16dbgError):
        MemoryRow.parse("RDY")

# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Breakpoint commands.

A breakpoint stops the CPU when execution reaches an address. Breakpoints are
keyed by location rather than by a slot id, so there is at most one per location
and clearing names the location, not an id. The full identity is the triple
(address, program K-bank, X16 RAM/ROM bank); for the common case (65C02, an
address below $A000) it collapses to just the address, with both banks fixed.
That is why these methods take a bank and an address and return no id, where the
overlapping ranges of watchpoints genuinely need slot ids.

A breakpoint in the $A000-$FFFF window is bank-specific: it fires only while its
X16 bank is the one currently mapped there, and that mapping changes at runtime
(the KERNAL runs in RAM bank 1, for one), so such a breakpoint is implicitly
scoped to the bank it was set in.

The toggle-at-cursor command (tb) belongs with the view-cursor family and is
deferred with it; this module covers the explicit-address set, clear, and list.
"""

from __future__ import annotations

from x16dbg.models import Breakpoint
from x16dbg.transport import Transport, formatHex


class BreakpointCommands:
    """Set, clear, and list breakpoints, mixed into the client facade."""

    transport: Transport

    def setBreakpoint(self, bank: int, addr: int, *, condition: str | None = None) -> None:
        """Arm a breakpoint at a bank and address, optionally conditional.

        Re-arming a location already set replaces it in place: the condition is
        updated, or cleared when none is given. The table holds up to 16
        breakpoints and the emulator rejects a further one once it is full.

        Args:
            bank: the X16 RAM/ROM bank, applied only for addresses in the
                $A000-$FFFF window; ignored (pass 00) for unbanked low memory.
            addr: the address to stop execution at.
            condition: an if-clause expression, or None for an unconditional break.
        """

        # sbp <bank> <addr> [if <cond>]
        parts = ["sbp", formatHex(bank, 2), formatHex(addr, 4)]

        # The condition is passed through verbatim, so the caller writes any
        # hex literals C-style (with a $ or 0x prefix), per the wire grammar.
        if condition is not None:
            parts.append("if")
            parts.append(condition)

        self.transport.command(" ".join(parts))

    def clearBreakpoint(self, bank: int, addr: int) -> None:
        """Clear the breakpoint at a bank and address.

        Args:
            bank: the bank of the breakpoint to clear.
            addr: the address of the breakpoint to clear.

        Raises:
            X16dbgError: when no breakpoint is set at that location.
        """

        # cbp <bank> <addr>; the emulator raises when nothing matches there.
        self.transport.command("cbp " + formatHex(bank, 2) + " " + formatHex(addr, 4))

    def clearAllBreakpoints(self) -> None:
        """Clear every breakpoint at once."""

        self.transport.command("cbp *")

    def enableBreakpoint(self, bank: int, addr: int) -> None:
        """Re-enable a disabled breakpoint so it stops the CPU again.

        Args:
            bank: the bank of the breakpoint to enable.
            addr: the address of the breakpoint to enable.

        Raises:
            X16dbgError: when no breakpoint is set at that location.
        """

        self.transport.command("bp " + formatHex(bank, 2) + " " + formatHex(addr, 4) + " on")

    def disableBreakpoint(self, bank: int, addr: int) -> None:
        """Mute a breakpoint without removing it, keeping its condition.

        Args:
            bank: the bank of the breakpoint to disable.
            addr: the address of the breakpoint to disable.

        Raises:
            X16dbgError: when no breakpoint is set at that location.
        """

        self.transport.command("bp " + formatHex(bank, 2) + " " + formatHex(addr, 4) + " off")

    def listBreakpoints(self) -> tuple[Breakpoint, ...]:
        """List the armed breakpoints in the order they were added.

        Returns:
            tuple[Breakpoint, ...]: one parsed breakpoint per active location,
            empty when none are set.
        """

        # An empty table returns no data lines, so the result is naturally empty.
        response = self.transport.command("lbp")
        breakpoints = tuple(Breakpoint.parse(line) for line in response.data)
        return breakpoints

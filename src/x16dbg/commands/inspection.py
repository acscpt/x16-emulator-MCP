# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Inspection commands.

Report machine state at the moment of the call: the cycle counter, the top of
the stack, the cc65 zero-page R0..R15 pseudo-registers, and VERA's state. These
read state and never change it.
"""

from __future__ import annotations

from x16dbg.models import StackEntry, VeraState
from x16dbg.transport import Transport, formatHex, parseHex


class InspectionCommands:
    """Read stack, zero-page registers, VERA state, and the clock."""

    transport: Transport

    def clocks(self) -> int:
        """Read the CPU cycles elapsed since the last resume.

        Returns:
            int: the cycle count (the wire value is decimal here, not hex).
        """

        # clk -> "clocks=<decimal>"; this is the one count the protocol gives
        # in decimal rather than hex.
        response = self.transport.command("clk")
        count = int(response.data[0].split("=", 1)[1])
        return count

    def stack(self, count: int = 16) -> tuple[StackEntry, ...]:
        """Read the top of the 6502 stack, most-recent push first.

        Args:
            count: the number of bytes to read (the emulator caps this at 0x40).

        Returns:
            tuple[StackEntry, ...]: one entry per byte, each its address and value.
        """

        # stk <count>; one "<addr>: <value>" row per byte.
        response = self.transport.command(f"stk {formatHex(count)}")
        entries = tuple(StackEntry.parse(line) for line in response.data)
        return entries

    def zeroPageRegisters(self) -> tuple[int, ...]:
        """Read the cc65 zero-page R0..R15 pseudo-registers.

        Returns:
            tuple[int, ...]: sixteen 16-bit values, indexed so element i is R<i>.
        """

        # zpr -> 16 lines "R<n>  <word>", already in order R0..R15; the value
        # is the second whitespace-separated token.
        response = self.transport.command("zpr")
        registers = tuple(parseHex(line.split()[1]) for line in response.data)
        return registers

    def veraState(self) -> VeraState:
        """Read a snapshot of VERA's internal state.

        Returns:
            VeraState: the parsed VERA register snapshot.
        """

        response = self.transport.command("vrg")
        state = VeraState.parse(response.data[0])
        return state

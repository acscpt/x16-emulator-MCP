# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Disassembly commands.

Disassemble instructions at an explicit address without moving the view cursor.
The line format (address, raw bytes, then a variable-width mnemonic and operand)
is not stable enough to parse safely, so the lines are returned verbatim; a
structured variant is a candidate emulator addition.
"""

from __future__ import annotations

from x16dbg.transport import Transport, formatHex


class DisasmCommands:
    """Disassemble memory, mixed into the client facade."""

    transport: Transport

    def disassemble(self, bank: int, addr: int, count: int) -> tuple[str, ...]:
        """Disassemble a number of instructions starting at an address.

        Args:
            bank: the CPU bank to disassemble from.
            addr: the 16-bit start address.
            count: the number of instructions (the emulator caps this at 0x40).

        Returns:
            tuple[str, ...]: one disassembly line per instruction, trailing
            whitespace trimmed.
        """

        # dis <bank> <addr> <count>; the lines are passed through, since their
        # internal layout is too variable to parse into fields reliably.
        command = f"dis {formatHex(bank, 2)} {formatHex(addr, 4)} {formatHex(count)}"
        response = self.transport.command(command)
        lines = tuple(line.rstrip() for line in response.data)
        return lines

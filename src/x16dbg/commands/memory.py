# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Memory commands.

This is the slice subset: read a block of CPU RAM as a typed dump, used to
inspect the bytes around a watchpoint hit.
"""

from __future__ import annotations

from x16dbg.models import MemoryDump
from x16dbg.transport import Transport, formatHex


class MemoryCommands:
    """Read CPU memory, mixed into the client facade."""

    transport: Transport

    def readMemory(self, bank: int, addr: int, count: int) -> MemoryDump:
        """Read a contiguous block of CPU RAM.

        Args:
            bank: the CPU bank to read from.
            addr: the 16-bit start address.
            count: the number of bytes to read (the emulator caps this at 0x1000).

        Returns:
            MemoryDump: the parsed rows of the read.
        """

        command = f"mem {formatHex(bank, 2)} {formatHex(addr, 4)} {formatHex(count)}"
        response = self.transport.command(command)
        dump = MemoryDump.parse(response.data)
        return dump

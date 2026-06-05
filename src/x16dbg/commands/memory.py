# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Memory commands.

Read, write, fill, and search CPU RAM with explicit arguments, separate from the
view-cursor family. Reads come back as a typed dump; a search returns the
addresses of its matches.
"""

from __future__ import annotations

from collections.abc import Iterable

from x16dbg.models import MemoryDump
from x16dbg.transport import Transport, formatHex, parseHex


class MemoryCommands:
    """Read, write, fill, and search CPU memory, mixed into the client facade."""

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

    def writeMemory(self, bank: int, addr: int, values: Iterable[int]) -> None:
        """Write consecutive bytes to CPU RAM, bypassing I/O side effects.

        The writes go straight to the RAM array, so the I/O region can be poked
        without triggering peripherals; for writes that should be seen by I/O,
        use fill.

        Args:
            bank: the CPU bank to write to.
            addr: the 16-bit start address.
            values: the byte values to write in order, starting at addr.
        """

        # wmm <bank> <addr> <hex>...; each value goes out as one byte of hex.
        hex_bytes = " ".join(formatHex(value, 2) for value in values)
        command = f"wmm {formatHex(bank, 2)} {formatHex(addr, 4)} {hex_bytes}"
        self.transport.command(command)

    def fill(self, bank: int, addr: int, value: int, count: int = 1) -> None:
        """Fill a range of CPU RAM with a byte through the CPU write path.

        Unlike writeMemory, the writes go through the CPU's write path, so an
        address in the I/O region triggers the same peripheral side effects a
        store instruction would.

        Args:
            bank: the CPU bank to write to.
            addr: the 16-bit start address.
            value: the byte written at each position.
            count: the number of bytes to write.
        """

        # fil <bank> <addr> <val> <count>; the count is sent even when it is 1.
        command = (
            f"fil {formatHex(bank, 2)} {formatHex(addr, 4)} "
            f"{formatHex(value, 2)} {formatHex(count)}"
        )
        self.transport.command(command)

    def find(self, bank: int, start: int, length: int, pattern: Iterable[int]) -> tuple[int, ...]:
        """Search a range of CPU RAM for a byte pattern.

        Args:
            bank: the CPU bank to search.
            start: the 16-bit start of the search range.
            length: the length of the range in bytes.
            pattern: the byte pattern to find (1 to 16 bytes).

        Returns:
            tuple[int, ...]: the start address of each match, empty when none.
        """

        # find <bank> <start> <len> <byte>...; matches come back one bare
        # address per line, and no data lines means nothing matched.
        hex_pattern = " ".join(formatHex(value, 2) for value in pattern)
        command = (
            f"find {formatHex(bank, 2)} {formatHex(start, 4)} {formatHex(length)} {hex_pattern}"
        )
        response = self.transport.command(command)
        matches = tuple(parseHex(line) for line in response.data)
        return matches

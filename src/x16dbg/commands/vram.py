# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""VRAM commands.

Read and write VERA's video RAM, a separate 17-bit address space (00000-1ffff)
with no bank. A read comes back in the same row format as a RAM dump, so it
reuses the MemoryDump model; only the address is five hex digits wide.
"""

from __future__ import annotations

from collections.abc import Iterable

from x16dbg.models import MemoryDump
from x16dbg.transport import Transport, formatHex


class VramCommands:
    """Read and write VRAM, mixed into the client facade."""

    transport: Transport

    def readVram(self, addr: int, count: int) -> MemoryDump:
        """Read a contiguous block of VRAM.

        Args:
            addr: the 17-bit VRAM start address.
            count: the number of bytes to read (the emulator caps this at 0x1000).

        Returns:
            MemoryDump: the parsed rows of the read, addressed in VRAM space.
        """

        # vmr <addr> <count>; VRAM takes no bank and uses 5-hex addresses.
        command = f"vmr {formatHex(addr, 5)} {formatHex(count)}"
        response = self.transport.command(command)
        dump = MemoryDump.parse(response.data)
        return dump

    def writeVram(self, addr: int, values: Iterable[int]) -> None:
        """Write consecutive bytes to VRAM, straight to the VRAM buffer.

        The writes bypass VERA's data-port mechanism, so they do not advance its
        address registers or touch its other state.

        Args:
            addr: the 17-bit VRAM start address.
            values: the byte values to write in order, starting at addr.
        """

        # vmw <addr> <hex>...; each value goes out as one byte of hex.
        hex_bytes = " ".join(formatHex(value, 2) for value in values)
        command = f"vmw {formatHex(addr, 5)} {hex_bytes}"
        self.transport.command(command)

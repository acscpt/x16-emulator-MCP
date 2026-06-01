# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Register commands.

This is the slice subset: read the CPU register snapshot, the context a hit is
inspected against.
"""

from __future__ import annotations

from x16dbg.models import Registers
from x16dbg.transport import Transport


class RegisterCommands:
    """Read the register file, mixed into the client facade."""

    transport: Transport

    def readRegisters(self) -> Registers:
        """Read and parse the CPU register snapshot.

        Returns:
            Registers: the parsed register state.
        """

        response = self.transport.command("reg")
        registers = Registers.parse(response.data[0])
        return registers

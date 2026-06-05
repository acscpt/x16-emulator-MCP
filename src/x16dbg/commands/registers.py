# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Register commands.

Read the CPU register snapshot (the context a hit is inspected against) and set
an individual register by name.
"""

from __future__ import annotations

from x16dbg.models import Registers
from x16dbg.transport import Transport, formatHex


class RegisterCommands:
    """Read and set the register file, mixed into the client facade."""

    transport: Transport

    def readRegisters(self) -> Registers:
        """Read and parse the CPU register snapshot.

        Returns:
            Registers: the parsed register state.
        """

        response = self.transport.command("reg")
        registers = Registers.parse(response.data[0])
        return registers

    def setRegister(self, name: str, value: int) -> None:
        """Set one CPU register to a value.

        Setting the program counter does not resume the CPU; follow with a
        resume to run from the new address.

        Args:
            name: the register name (pc, a, b, c, x, y, sp, p, k, db, dp, e).
            value: the new value; the emulator takes the width from the register.

        Raises:
            X16dbgError: when the register name is not recognised.
        """

        # srg <name> <hex>; the width is implied by the register, so the value
        # goes out as bare hex with no padding.
        self.transport.command("srg " + name + " " + formatHex(value))

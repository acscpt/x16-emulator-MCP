# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Watchpoint commands.

A watchpoint stops the CPU when it reads or writes a watched location, naming
the instruction that made the access. This module arms one over a byte or a
range, optionally conditional; lists the armed set as typed results; enables or
disables one without removing it; and clears one or all.
"""

from __future__ import annotations

import re

from x16dbg.models import AccessType, Watchpoint
from x16dbg.transport import Transport, X16dbgError, formatHex

# The echo a successful swp prints: "wp <id> set".
_WP_SET_RE = re.compile(r"^wp (?P<id>\d+) set$")


class WatchpointCommands:
    """Arm, list, and clear watchpoints, mixed into the client facade."""

    transport: Transport

    def setWatchpoint(
        self,
        access: AccessType | str,
        bank: int,
        addr: int,
        *,
        end: int | None = None,
        condition: str | None = None,
    ) -> int:
        """Arm a watchpoint and return its assigned slot id.

        Args:
            access: the access type to watch (read, write, or read/write).
            bank: the bank of the watched location.
            addr: the watched address, or the start of a range.
            end: the inclusive end of a watched range, or None for a single byte.
            condition: a condition expression for the if clause, or None.

        Returns:
            int: the slot id the emulator assigned to the watchpoint.

        Raises:
            X16dbgError: when the set echo cannot be found in the reply.
        """

        access_value = access.value if isinstance(access, AccessType) else access

        # swp [r|w|rw] <bank> <addr> [end] [if <cond>]
        parts = ["swp", access_value, formatHex(bank, 2), formatHex(addr, 4)]

        if end is not None:
            parts.append(formatHex(end, 4))

        if condition is not None:
            parts.append("if")
            parts.append(condition)

        response = self.transport.command(" ".join(parts))
        slot_id = self._parseAssignedId(response.data)
        return slot_id

    def listWatchpoints(self) -> tuple[Watchpoint, ...]:
        """List the armed watchpoints as typed results.

        Returns:
            tuple[Watchpoint, ...]: one parsed watchpoint per slot, empty when
            none are armed.
        """

        # An empty table returns no data lines, so the result is naturally empty.
        response = self.transport.command("lwp")
        watchpoints = tuple(Watchpoint.parse(line) for line in response.data)
        return watchpoints

    def enableWatchpoint(self, slot_id: int) -> None:
        """Re-enable a disabled watchpoint so it fires again.

        Args:
            slot_id: the slot id of the watchpoint to enable.

        Raises:
            X16dbgError: when the slot holds no watchpoint.
        """

        self.transport.command("wp " + str(slot_id) + " on")

    def disableWatchpoint(self, slot_id: int) -> None:
        """Mute a watchpoint without removing it, keeping its definition and hits.

        Args:
            slot_id: the slot id of the watchpoint to disable.

        Raises:
            X16dbgError: when the slot holds no watchpoint.
        """

        self.transport.command("wp " + str(slot_id) + " off")

    def clearWatchpoint(self, which: int | str) -> None:
        """Clear one watchpoint by id, or all of them with "*".

        Args:
            which: the slot id to clear, or "*" to clear every watchpoint.
        """

        argument = "*" if which == "*" else str(which)
        self.transport.command("cwp " + argument)

    def _parseAssignedId(self, data: list[str]) -> int:
        """Read the assigned slot id from a swp reply's data lines.

        Args:
            data: the data lines returned by swp.

        Returns:
            int: the assigned slot id.

        Raises:
            X16dbgError: when no "wp <id> set" line is present.
        """

        for line in data:
            match = _WP_SET_RE.match(line)

            if match is not None:
                slot_id = int(match["id"])
                return slot_id

        raise X16dbgError(f"watchpoint set echo not found in {data}")

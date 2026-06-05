# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Session commands.

Query the current machine mode, read the full state snapshot, and control which
per-prompt header lines the emulator emits.
"""

from __future__ import annotations

from x16dbg.transport import Transport


class SessionCommands:
    """Query mode and state and control the header, mixed into the client facade."""

    transport: Transport

    def mode(self) -> str:
        """Report the current machine mode.

        Returns:
            str: the mode, one of "stop", "run", or "step".
        """

        # mod -> "mode=<mode> pc=<bank>:<addr>"; take the mode token's value.
        response = self.transport.command("mod")
        mode = response.data[0].split(maxsplit=1)[0].split("=", 1)[1]
        return mode

    def state(self) -> tuple[str, ...]:
        """Read the full debugger state snapshot as labeled rows.

        The snapshot is formatted for reading rather than parsing (mode, the
        view cursor, the CPU program counter, the clock, and any breakpoints),
        so the rows are returned verbatim.

        Returns:
            tuple[str, ...]: the state rows, trailing whitespace trimmed.
        """

        response = self.transport.command("st")
        rows = tuple(line.rstrip() for line in response.data)
        return rows

    def setHeaders(self, on: bool) -> None:
        """Show or suppress all per-prompt header lines.

        Args:
            on: True to show the header lines, False to suppress them.
        """

        self.transport.command("hdr " + ("on" if on else "off"))

    def setHeaderLine(self, line: str | int, on: bool) -> None:
        """Show or suppress a single header line.

        Args:
            line: the header line, by name (cpu, aux, view, bp) or number (1-4).
            on: True to show the line, False to suppress it.
        """

        self.transport.command(f"hdr {line} " + ("on" if on else "off"))

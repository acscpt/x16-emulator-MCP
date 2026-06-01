# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Execution-control commands.

This is the slice subset: resume the CPU, and resume-and-report the next
stopping event, which is the heart of the memory-corruption hunt loop.
"""

from __future__ import annotations

from x16dbg.models import BreakEvent, WatchHit
from x16dbg.transport import Transport

# The event prefixes that mean the CPU has stopped again after a resume.
_STOP_PREFIXES = ("* WP ", "* BRK ")


class ExecutionCommands:
    """Resume and run-until, mixed into the client facade."""

    transport: Transport
    last_event: WatchHit | BreakEvent | None

    def cont(self) -> None:
        """Resume the CPU from STOP."""

        self.transport.command("cnt")

    def runUntil(self, *, timeout: float | None = None) -> WatchHit | BreakEvent | None:
        """Resume the CPU and return the next watchpoint or break event.

        The stopping event can arrive with the resume's own prompt or on the
        following one, so the transport collects from both. The returned event
        is also recorded as the last stopping event.

        Args:
            timeout: seconds to wait for the stopping event, or None for the default.

        Returns:
            WatchHit | BreakEvent | None: the stopping event, or None if none arrived.
        """

        events = self.transport.resumeCollectingEvents(
            "cnt", until_prefix=_STOP_PREFIXES, timeout=timeout
        )

        stop = self._findStopEvent(events)
        self.last_event = stop
        return stop

    def _findStopEvent(self, events: list[str]) -> WatchHit | BreakEvent | None:
        """Parse the first watchpoint or break event from a list of event lines.

        Args:
            events: the collected event lines.

        Returns:
            WatchHit | BreakEvent | None: the parsed stopping event, or None.
        """

        for event in events:
            # A watchpoint hit names the culprit access and program counter.
            if event.startswith("* WP "):
                hit = WatchHit.parse(event)
                return hit

            # A break names why and where the CPU stopped.
            if event.startswith("* BRK "):
                brk = BreakEvent.parse(event)
                return brk

        return None

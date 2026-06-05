# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Per-category command mixins, each a thin layer over the transport.

Each module here mirrors one section of the emulator's command reference and
contributes a mixin that the client facade composes into one flat API.
"""

from __future__ import annotations

from x16dbg.commands.breakpoints import BreakpointCommands
from x16dbg.commands.capture import CaptureCommands
from x16dbg.commands.disasm import DisasmCommands
from x16dbg.commands.execution import ExecutionCommands
from x16dbg.commands.inspection import InspectionCommands
from x16dbg.commands.memory import MemoryCommands
from x16dbg.commands.registers import RegisterCommands
from x16dbg.commands.session import SessionCommands
from x16dbg.commands.vram import VramCommands
from x16dbg.commands.watchpoints import WatchpointCommands

__all__ = [
    "ExecutionCommands",
    "BreakpointCommands",
    "WatchpointCommands",
    "RegisterCommands",
    "MemoryCommands",
    "VramCommands",
    "DisasmCommands",
    "InspectionCommands",
    "CaptureCommands",
    "SessionCommands",
]

# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""x16dbg: a pure-Python client harness for the Commander X16 emulator's
stdio debugger (``-debugstdio``).

The package has no third-party dependencies. It exposes the runtime-input
discovery helpers and the transport core that drives the debugger protocol.
"""

from __future__ import annotations

from x16dbg.client import Client
from x16dbg.config import discoverEmulator, discoverPrg, discoverRom
from x16dbg.models import (
    AccessType,
    BreakEvent,
    Breakpoint,
    BreakReason,
    MemoryDump,
    MemoryRow,
    Registers,
    StackEntry,
    VeraState,
    WatchHit,
    Watchpoint,
)
from x16dbg.transport import (
    PROTOCOL_VERSION,
    Response,
    Transport,
    X16dbgError,
    X16ProtocolError,
    formatHex,
    parseHex,
)

__version__ = "0.1.5"

__all__ = [
    "discoverEmulator",
    "discoverRom",
    "discoverPrg",
    "Client",
    "Transport",
    "Response",
    "X16dbgError",
    "X16ProtocolError",
    "PROTOCOL_VERSION",
    "parseHex",
    "formatHex",
    "AccessType",
    "BreakReason",
    "WatchHit",
    "Watchpoint",
    "BreakEvent",
    "Breakpoint",
    "Registers",
    "MemoryRow",
    "MemoryDump",
    "StackEntry",
    "VeraState",
    "__version__",
]

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
    BreakReason,
    MemoryDump,
    MemoryRow,
    Registers,
    WatchHit,
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

__version__ = "0.1.0"

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
    "BreakEvent",
    "Registers",
    "MemoryRow",
    "MemoryDump",
    "__version__",
]

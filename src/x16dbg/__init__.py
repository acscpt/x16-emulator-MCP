# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""x16dbg: a pure-Python client harness for the Commander X16 emulator's
stdio debugger (``-debugstdio``).

The package has no third-party dependencies and exposes the runtime-input
discovery helpers for the emulator binary, ROM, and PRG.
"""

from __future__ import annotations

from x16dbg.config import discoverEmulator, discoverPrg, discoverRom

__version__ = "0.1.0"

__all__ = ["discoverEmulator", "discoverRom", "discoverPrg", "__version__"]

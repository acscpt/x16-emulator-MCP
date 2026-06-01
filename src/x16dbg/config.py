# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Discovery of the external runtime inputs: the emulator binary, the ROM,
and an optional PRG to boot.

None of these are packaged. They are found in a fixed order so a developer
can either point at them explicitly, set an environment variable, or drop
them into the repo-root ``resources/`` folder and have everything resolve
with no configuration:

    explicit argument  ->  environment variable  ->  search path

The search path leads with ``resources/`` (git-excluded, so the
separately-licensed ROM and the prebuilt binary never enter the repo) and
then falls back to the same defaults the emulator's ``x16dbg_smoke.py`` uses.
"""

from __future__ import annotations

import os
from pathlib import Path

# resources/ sits at the repository root, two levels above this file
# (src/x16dbg/config.py -> src -> repo root).
_REPO_ROOT = Path(__file__).resolve().parents[2]
_RESOURCES = _REPO_ROOT / "resources"


def _firstExisting(candidates: list[Path], *, executable: bool = False) -> Path | None:
    """Return the first candidate that exists, and is executable when asked.

    Args:
        candidates: paths to test, in priority order.
        executable: when True, require the file to be executable.

    Returns:
        Path | None: the resolved first match, or None when none qualify.
    """

    for candidate in candidates:
        # Skip anything that is not a real file on disk.
        if not candidate.is_file():
            continue

        # When an executable is required, a present but non-executable file
        # does not qualify.
        if executable and not os.access(candidate, os.X_OK):
            continue

        resolved = candidate.resolve()
        return resolved

    return None


def discoverEmulator(explicit: str | os.PathLike[str] | None = None) -> Path | None:
    """Locate the x16emu binary.

    Args:
        explicit: caller-supplied path tried ahead of any search.

    Returns:
        Path | None: the resolved binary path, or None when not found.
    """

    candidates: list[Path] = []

    # Explicit argument first, then the environment override.
    if explicit:
        candidates.append(Path(explicit))

    env = os.environ.get("X16EMU_PATH")

    if env:
        candidates.append(Path(env))

    # Then the search path, led by the local resources/ folder.
    candidates += [
        _RESOURCES / "x16emu",
        Path("build/x16emu"),
        Path("../build/x16emu"),
        Path("x16emu"),
        Path("../x16emu"),
    ]

    found = _firstExisting(candidates, executable=True)
    return found


def discoverRom(explicit: str | os.PathLike[str] | None = None) -> Path | None:
    """Locate rom.bin.

    Args:
        explicit: caller-supplied path tried ahead of any search.

    Returns:
        Path | None: the resolved ROM path, or None when not found.
    """

    candidates: list[Path] = []

    # Explicit argument first, then the environment override.
    if explicit:
        candidates.append(Path(explicit))

    env = os.environ.get("X16ROM_PATH")

    if env:
        candidates.append(Path(env))

    # Then the search path: resources/, the emulator's user data dir, cwd.
    candidates += [
        _RESOURCES / "rom.bin",
        Path.home() / ".local/share/x16emu/rom.bin",
        Path("rom.bin"),
        Path("../rom.bin"),
    ]

    found = _firstExisting(candidates)
    return found


def discoverPrg(explicit: str | os.PathLike[str] | None = None) -> Path | None:
    """Locate an optional PRG to boot.

    A PRG is normally passed per session rather than discovered, but an
    explicit path, X16PRG_PATH, or a single .prg dropped in resources/ is
    honoured as a default.

    Args:
        explicit: caller-supplied path tried ahead of the environment and resources/.

    Returns:
        Path | None: the resolved PRG path, or None when there is none.
    """

    candidates: list[Path] = []

    # An explicit path or X16PRG_PATH takes precedence over resources/.
    if explicit:
        candidates.append(Path(explicit))

    env = os.environ.get("X16PRG_PATH")

    if env:
        candidates.append(Path(env))

    found = _firstExisting(candidates)

    if found:
        return found

    # Otherwise accept a single .prg dropped into resources/.
    if _RESOURCES.is_dir():
        prgs = sorted(_RESOURCES.glob("*.prg"))

        if prgs:
            resolved = prgs[0].resolve()
            return resolved

    return None

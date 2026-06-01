# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Discovery of the emulator binary, ROM, and optional PRG.

Covers the resolution order (explicit argument, environment variable, then
the resources/ search path) without needing the real binary present.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from x16dbg.config import discoverEmulator, discoverPrg, discoverRom


def testExplicitEmulatorPathWins(tmp_path: Path) -> None:
    """An explicit executable path is returned ahead of any search path.

    Args:
        tmp_path: pytest temporary directory for the fake binary.
    """

    fake = tmp_path / "x16emu"
    fake.write_bytes(b"\x7fELF")
    os.chmod(fake, 0o755)

    assert discoverEmulator(explicit=fake) == fake.resolve()


def testNonExecutableEmulatorIsRejected(tmp_path: Path) -> None:
    """A non-executable candidate is skipped, not returned.

    Args:
        tmp_path: pytest temporary directory for the fake binary.
    """

    fake = tmp_path / "x16emu"
    fake.write_bytes(b"not a binary")
    os.chmod(fake, 0o644)

    assert discoverEmulator(explicit=fake) != fake.resolve()


def testRomEnvOverride(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """X16ROM_PATH is honoured when set.

    Args:
        tmp_path: pytest temporary directory for the fake ROM.
        monkeypatch: pytest fixture used to set the environment variable.
    """

    fake = tmp_path / "rom.bin"
    fake.write_bytes(b"\x00" * 16)
    monkeypatch.setenv("X16ROM_PATH", str(fake))

    assert discoverRom() == fake.resolve()


def testPrgEnvOverride(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """X16PRG_PATH is honoured when set.

    Args:
        tmp_path: pytest temporary directory for the fake PRG.
        monkeypatch: pytest fixture used to set the environment variable.
    """

    fake = tmp_path / "app.prg"
    fake.write_bytes(b"\x01\x08")
    monkeypatch.setenv("X16PRG_PATH", str(fake))

    assert discoverPrg() == fake.resolve()


def testEmulatorDiscoveredFromResources(emulatorBinary: Path) -> None:
    """The bundled resources/ binary resolves with no configuration.

    Args:
        emulatorBinary: the discovered emulator path fixture.
    """

    assert emulatorBinary.is_file()
    assert os.access(emulatorBinary, os.X_OK)


def testRomDiscoveredFromResources(romPath: Path) -> None:
    """The bundled resources/ ROM resolves with no configuration.

    Args:
        romPath: the discovered ROM path fixture.
    """

    assert romPath.is_file()
    assert romPath.name == "rom.bin"

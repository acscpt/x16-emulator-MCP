# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Screen-capture commands against the live emulator.

Confirm a screenshot comes back as PNG bytes, both with a temp file and to an
explicit path, even under the headless dummy video driver.
"""

from __future__ import annotations

from pathlib import Path

from x16dbg.client import Client

# The 8-byte PNG file signature.
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def testScreenshotReturnsPngBytes(client: Client) -> None:
    """A screenshot with no path returns PNG bytes from a temp file.

    Args:
        client: the connected client fixture.
    """

    client.brk()

    data = client.screenshot()

    assert data[:8] == _PNG_MAGIC
    assert len(data) > 8


def testScreenshotWritesToGivenPath(client: Client, tmp_path: Path) -> None:
    """A screenshot to an explicit path writes that file and returns its bytes.

    Args:
        client: the connected client fixture.
        tmp_path: a pytest temporary directory.
    """

    client.brk()
    target = tmp_path / "shot.png"

    data = client.screenshot(target)

    assert target.exists()
    assert data[:8] == _PNG_MAGIC

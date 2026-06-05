# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Screen-capture commands.

Capture the composited VERA output as a PNG. The emulator writes the file and
echoes its path; the harness reads the bytes back, so the agent's "look at the
screen" primitive is a single call returning image data.
"""

from __future__ import annotations

import os
import tempfile

from x16dbg.transport import Transport


class CaptureCommands:
    """Capture the screen, mixed into the client facade."""

    transport: Transport

    def screenshot(self, path: str | os.PathLike[str] | None = None) -> bytes:
        """Capture the current screen and return the PNG bytes.

        The emulator composes a frame from live VERA state on demand, so this
        works headless. With no path, a temporary file is used and removed once
        its bytes are read; a given path is written and left in place.

        Args:
            path: where the emulator should write the PNG, or None for a temp file.

        Returns:
            bytes: the PNG image data.
        """

        # With no path, reserve a temp name; the emulator writes the file, so
        # only its name is needed here, not an open handle.
        temporary = path is None

        if temporary:
            handle, target = tempfile.mkstemp(suffix=".png", prefix="x16scr-")
            os.close(handle)
        else:
            target = os.fspath(path)

        # scr writes the PNG and echoes the path; read that path back, then drop
        # the temp file once its bytes are in hand.
        try:
            response = self.transport.command(f"scr {target}")
            written = response.data[0] if response.data else target

            with open(written, "rb") as image:
                data = image.read()

        finally:
            if temporary:
                os.unlink(target)

        return data

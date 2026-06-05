# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""The Phase 1 client facade.

The client composes the per-category command mixins over one transport into a
single flat API, the object tests and the MCP server drive. It owns the
lifecycle: launch builds and connects the transport, and the client closes it.
"""

from __future__ import annotations

import os

from x16dbg.commands import (
    BreakpointCommands,
    CaptureCommands,
    DisasmCommands,
    ExecutionCommands,
    InspectionCommands,
    MemoryCommands,
    RegisterCommands,
    SessionCommands,
    VramCommands,
    WatchpointCommands,
)
from x16dbg.models import BreakEvent, WatchHit
from x16dbg.transport import PROTOCOL_VERSION, Transport


class Client(
    ExecutionCommands,
    BreakpointCommands,
    WatchpointCommands,
    RegisterCommands,
    MemoryCommands,
    VramCommands,
    DisasmCommands,
    InspectionCommands,
    CaptureCommands,
    SessionCommands,
):
    """A connected debugger client over one emulator session."""

    def __init__(self, transport: Transport) -> None:
        """Wrap a connected transport and start with no recorded stopping event.

        Args:
            transport: a connected transport to drive.
        """

        self.transport = transport
        self.last_event: WatchHit | BreakEvent | None = None

    @classmethod
    def launch(
        cls,
        emulator: str | os.PathLike[str],
        rom: str | os.PathLike[str],
        *,
        prg: str | os.PathLike[str] | None = None,
        load_addr: int | None = None,
        run: bool = False,
        startup_bp: int | None = None,
        warp: bool = True,
        require_proto: int | None = PROTOCOL_VERSION,
        command_timeout: float = 2.0,
        event_timeout: float = 5.0,
    ) -> Client:
        """Spawn the emulator and return a connected client.

        Args:
            emulator: path to the x16emu binary.
            rom: path to rom.bin.
            prg: optional PRG to load from the host filesystem.
            load_addr: optional override load address for the PRG (hex value).
            run: when True, autostart the loaded program with BASIC RUN.
            startup_bp: optional hex address to break at on startup.
            warp: when True, remove the speed throttle.
            require_proto: protocol version to require, or None to skip the gate.
            command_timeout: seconds to wait for a command's prompt.
            event_timeout: seconds to wait for an asynchronous event prompt.

        Returns:
            Client: the connected client.
        """

        transport = Transport(
            emulator,
            rom,
            prg=prg,
            load_addr=load_addr,
            run=run,
            startup_bp=startup_bp,
            warp=warp,
            require_proto=require_proto,
            command_timeout=command_timeout,
            event_timeout=event_timeout,
        )

        client = cls(transport)
        return client

    @property
    def protocolVersion(self) -> int | None:
        """The protocol version the session reported at startup.

        Returns:
            int | None: the version, or None when it was not read.
        """

        version = self.transport.proto_version
        return version

    def __enter__(self) -> Client:
        """Enter the context manager.

        Returns:
            Client: this instance.
        """

        return self

    def __exit__(self, *_: object) -> None:
        """Close the session on context exit."""

        self.close()

    def close(self) -> None:
        """Close the underlying transport and its emulator process."""

        self.transport.close()

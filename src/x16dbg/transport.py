# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""The transport core: the only module that talks to the emulator over the wire.

Everything above this layer formats command strings and parses the lines that
come back; this module owns the subprocess, the read-until-prompt loop, the
split of a response into data, events, and header lines, the warp-speed event
race, and the mapping of an ``ERR`` reply to an exception.

The protocol is line-based ASCII. A command goes in on one line; zero or more
data lines come back, then a terminator (``RDY`` or ``ERR <message>``), then up
to four header lines, then the prompt ``x16db > `` with no trailing newline.
Asynchronous events (``* BRK``, ``* RES``, ``* WP``, ``* BP``) arrive on their
own lines between a response and the next prompt.
"""

from __future__ import annotations

import os
import select
import subprocess
import time
from dataclasses import dataclass, field

# The debugger prompt. It has no trailing newline, so a reader cannot use
# readline; it reads until the buffer ends with these bytes.
_PROMPT = b"x16db > "

# Header lines are prefixed "N: [" for N in 1..4.
_HEADER_PREFIXES = tuple(f"{n}: [" for n in range(1, 5))

# The protocol version this client is written against.
PROTOCOL_VERSION = 2


class X16dbgError(Exception):
    """Raised when the debugger replies with ERR or the protocol misbehaves."""


class X16ProtocolError(X16dbgError):
    """Raised when the emulator reports a protocol version we do not support."""


@dataclass
class Response:
    """The parsed result of reading up to one prompt.

    Attributes:
        data: the free-form data lines the command produced.
        events: asynchronous event lines (those starting with "* ").
        header: the status header lines that precede the prompt.
        terminator: "RDY", an "ERR ..." string, or None when the read carried
            no terminator (as when passively waiting for an async event).
    """

    data: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    header: list[str] = field(default_factory=list)
    terminator: str | None = None


def parseHex(text: str) -> int:
    """Parse a bare hex number, the protocol's convention outside conditions.

    Args:
        text: a hex string with no prefix, such as "c010".

    Returns:
        int: the parsed value.
    """

    value = int(text, 16)
    return value


def formatHex(value: int, width: int = 0) -> str:
    """Format an integer as bare lowercase hex, the protocol's wire form.

    Args:
        value: the number to format.
        width: minimum width, zero-padded; 0 leaves it unpadded.

    Returns:
        str: the lowercase hex string with no prefix.
    """

    text = format(value, f"0{width}x") if width else format(value, "x")
    return text


class Transport:
    """Owns one emulator subprocess and drives the stdio debugger protocol.

    The process is spawned and the startup handshake (banner, prompt, and the
    ``ver`` gate) runs on construction, so a constructed Transport is ready to
    take commands. It is a context manager and closes the process on exit.
    """

    def __init__(
        self,
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
    ) -> None:
        """Spawn the emulator headless and run the startup handshake.

        Args:
            emulator: path to the x16emu binary.
            rom: path to rom.bin.
            prg: optional PRG to load from the host filesystem.
            load_addr: optional override load address for the PRG (hex value).
            run: when True, autostart the loaded program with BASIC RUN.
            startup_bp: optional hex address to break at on startup.
            warp: when True, remove the speed throttle (the usual harness mode).
            require_proto: protocol version to require, or None to skip the gate.
            command_timeout: seconds to wait for a command's prompt.
            event_timeout: seconds to wait for an asynchronous event prompt.

        Raises:
            X16ProtocolError: when the emulator reports an unsupported version.
        """

        self._command_timeout = command_timeout
        self._event_timeout = event_timeout
        self.last_header: list[str] = []
        self.proto_version: int | None = None

        # Bytes read past one prompt are retained here for the next read, so the
        # prompt is treated as a record separator rather than a trailing marker.
        self._buf = b""

        # Headless: the dummy SDL drivers open no window and no audio device.
        env = os.environ.copy()
        env["SDL_VIDEODRIVER"] = "dummy"
        env["SDL_AUDIODRIVER"] = "dummy"

        args = self._buildArgs(emulator, rom, prg, load_addr, run, startup_bp, warp)

        self.proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            bufsize=0,
        )

        # Run the handshake; on any failure, do not leak the subprocess.
        try:
            self._handshake(require_proto)

        except BaseException:
            self.close()
            raise

    @staticmethod
    def _buildArgs(
        emulator: str | os.PathLike[str],
        rom: str | os.PathLike[str],
        prg: str | os.PathLike[str] | None,
        load_addr: int | None,
        run: bool,
        startup_bp: int | None,
        warp: bool,
    ) -> list[str]:
        """Assemble the emulator command line from the launch options.

        Args:
            emulator: path to the x16emu binary.
            rom: path to rom.bin.
            prg: optional PRG to load.
            load_addr: optional hex load address appended to the PRG argument.
            run: when True, append -run to autostart the program.
            startup_bp: optional hex startup breakpoint after -debugstdio.
            warp: when True, append -warp.

        Returns:
            list[str]: the argv for the subprocess.
        """

        args = [str(emulator), "-rom", str(rom)]

        # A PRG is loaded from the host filesystem, with an optional load
        # address (bare hex) and an optional autostart.
        if prg is not None:
            prg_arg = str(prg)

            if load_addr is not None:
                prg_arg += "," + formatHex(load_addr)

            args += ["-prg", prg_arg]

            if run:
                args.append("-run")

        # The debugger frontend, with an optional startup breakpoint address.
        args.append("-debugstdio")

        if startup_bp is not None:
            args.append(formatHex(startup_bp))

        if warp:
            args.append("-warp")

        return args

    def __enter__(self) -> Transport:
        """Enter the context manager.

        Returns:
            Transport: this instance.
        """

        return self

    def __exit__(self, *_: object) -> None:
        """Close the subprocess on context exit."""

        self.close()

    def close(self) -> None:
        """Ask the emulator to quit, then wait for it, killing it if it lingers."""

        if self.proc.poll() is None:
            # A best-effort clean quit; the pipe may already be gone.
            try:
                self.proc.stdin.write(b"quit\n")
                self.proc.stdin.flush()

            except OSError:
                pass

        try:
            self.proc.wait(timeout=2)

        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()

    def _handshake(self, require_proto: int | None) -> None:
        """Read the startup banner and prompt, then gate on the protocol version.

        Args:
            require_proto: the version to require, or None to record without gating.

        Raises:
            X16ProtocolError: when the reported version does not match.
        """

        # The emulator prints a banner and the first prompt; discard them.
        self._readUntilPrompt(self._command_timeout)

        # Read the protocol version and store it.
        response = self.command("ver")
        proto_line = response.data[0] if response.data else ""
        self.proto_version = parseHex(proto_line.split("=", 1)[1]) if "=" in proto_line else None

        if require_proto is not None and self.proto_version != require_proto:
            raise X16ProtocolError(
                f"unsupported protocol version: got {proto_line!r}, expected proto={require_proto}"
            )

    def _readUntilPrompt(self, timeout: float) -> str:
        """Read one prompt-delimited response, retaining anything past the prompt.

        The prompt is a record separator, not just a trailing marker: an
        asynchronous event (a breakpoint or watchpoint firing) arrives on its
        own line carrying its own prompt, so a single read can contain several.
        This returns the body up to the first prompt and keeps the remainder
        buffered for the next call, so each read consumes exactly one prompt and
        a mid-stream prompt never leaks into the parsed lines.

        Args:
            timeout: seconds to wait for the prompt to arrive.

        Returns:
            str: the decoded text before the first prompt in the stream.

        Raises:
            TimeoutError: when no prompt arrives within the timeout.
            EOFError: when the emulator closes stdout before a prompt.
        """

        deadline = time.monotonic() + timeout

        # Read more only until the retained buffer holds at least one full prompt.
        while _PROMPT not in self._buf:
            remaining = deadline - time.monotonic()

            if remaining <= 0:
                raise TimeoutError(f"no prompt within {timeout}s; buffer={self._buf!r}")

            ready, _, _ = select.select([self.proc.stdout], [], [], min(0.05, remaining))

            if not ready:
                continue

            chunk = os.read(self.proc.stdout.fileno(), 4096)

            if not chunk:
                raise EOFError(f"emulator closed stdout before a prompt; buffer={self._buf!r}")

            self._buf += chunk

        # Split at the first prompt; the tail (a queued async event, say) stays
        # buffered for the next read.
        head, _, self._buf = self._buf.partition(_PROMPT)
        body = head.decode("ascii", errors="replace")
        return body

    def send(self, line: str) -> None:
        """Write one command line, terminated with a newline, and flush.

        Args:
            line: the command to send, without a trailing newline.
        """

        self.proc.stdin.write((line + "\n").encode("ascii"))
        self.proc.stdin.flush()

    def _parseBody(self, body: str) -> Response:
        """Split a prompt-terminated body into data, events, header, terminator.

        Args:
            body: the text read before a prompt.

        Returns:
            Response: the classified lines, with the header recorded on the
            instance as the most recent header seen.
        """

        response = Response()

        for raw in body.split("\n"):
            line = raw.rstrip("\r")

            # Blank separators carry no information.
            if line == "":
                continue

            if line == "RDY":
                response.terminator = "RDY"

            elif line.startswith("ERR"):
                response.terminator = line

            elif line.startswith("* "):
                response.events.append(line)

            elif line.startswith(_HEADER_PREFIXES):
                response.header.append(line)

            else:
                response.data.append(line)

        self.last_header = response.header
        return response

    def command(self, line: str, *, timeout: float | None = None) -> Response:
        """Send a command and read until the next prompt, raising on ERR.

        Args:
            line: the command to send.
            timeout: seconds to wait for the prompt, or None for the default.

        Returns:
            Response: the data, events, and header from the reply.

        Raises:
            X16dbgError: when the reply is ERR, or no terminator arrives.
        """

        self.send(line)

        wait = self._command_timeout if timeout is None else timeout

        # A command's reply ends in RDY or ERR. An asynchronous event (its own
        # line plus its own prompt, with no terminator) can sit ahead of that
        # reply in the stream, so read past such event-only responses, keeping
        # their events, until the reply that actually terminates arrives.
        reply = Response()

        while True:
            body = self._readUntilPrompt(wait)
            chunk = self._parseBody(body)

            reply.events += chunk.events

            if chunk.terminator is not None:
                reply.data = chunk.data
                reply.header = chunk.header
                reply.terminator = chunk.terminator
                break

        if reply.terminator.startswith("ERR"):
            raise X16dbgError(f"{line!r}: {reply.terminator}")

        return reply

    def waitPrompt(self, *, timeout: float | None = None) -> Response:
        """Read the next prompt without sending anything.

        This observes asynchronous events that arrive while the CPU is running,
        such as a breakpoint or watchpoint hit after a resume.

        Args:
            timeout: seconds to wait for the prompt, or None for the event default.

        Returns:
            Response: the data, events, and header read before the prompt.
        """

        body = self._readUntilPrompt(self._event_timeout if timeout is None else timeout)
        response = self._parseBody(body)
        return response

    def resumeCollectingEvents(
        self,
        line: str = "cnt",
        *,
        until_prefix: str | tuple[str, ...] | None = None,
        timeout: float | None = None,
    ) -> list[str]:
        """Resume the CPU and collect events from this read and the next prompt.

        At warp a breakpoint or watchpoint can emit its event in the same read
        as the resume's own prompt, or asynchronously on the following prompt.
        This sends the resume, takes the immediate events, and waits one more
        prompt when the awaited event has not yet been seen.

        Args:
            line: the resume command to send (cnt, stp, sov).
            until_prefix: an event prefix, or tuple of prefixes, to wait for; or
                None to take one extra prompt's worth of events regardless.
            timeout: seconds to wait for the follow-up prompt, or None for the
                event default.

        Returns:
            list[str]: the event lines collected from both reads.
        """

        response = self.command(line)
        events = list(response.events)

        # Decide whether the awaited event has already arrived.
        if until_prefix is None:
            satisfied = False
        else:
            satisfied = any(event.startswith(until_prefix) for event in events)

        # Otherwise wait one more prompt for the async event, tolerating a
        # timeout so a caller's assertion fails cleanly rather than hanging.
        if not satisfied:
            try:
                extra = self.waitPrompt(timeout=timeout)
                events += extra.events

            except TimeoutError:
                pass

        return events

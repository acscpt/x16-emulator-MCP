# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""The transport's prompt handling, exercised against scripted byte streams.

These replay the exact wire patterns that desynced an earlier build: an
asynchronous event carries its own prompt with no RDY, so a single read can hold
several prompts. The prompt is a record separator, and the transport must
consume exactly one per response, drain a pending event ahead of a reply, and
never fold a mid-stream prompt into the parsed data. No emulator is needed, so
these run everywhere and pin the behaviour deterministically.
"""

from __future__ import annotations

import os

from x16dbg.transport import Transport


class _Stdout:
    """A stand-in for the subprocess stdout backed by a raw pipe fd."""

    def __init__(self, fd: int) -> None:
        """Hold the read end of the pipe.

        Args:
            fd: the file descriptor to read scripted bytes from.
        """

        self._fd = fd

    def fileno(self) -> int:
        """Return the descriptor, for select and os.read.

        Returns:
            int: the read-end file descriptor.
        """

        return self._fd

    def close(self) -> None:
        """Close the descriptor."""

        os.close(self._fd)


class _Stdin:
    """A stand-in for the subprocess stdin that discards what is written."""

    def write(self, _data: bytes) -> None:
        """Discard a write."""

    def flush(self) -> None:
        """Discard a flush."""


def _transportFeeding(script: bytes) -> Transport:
    """Build a Transport whose stdout replays scripted bytes, with no subprocess.

    Args:
        script: the exact bytes the emulator is to appear to have sent.

    Returns:
        Transport: an unspawned transport wired to the scripted stream.
    """

    # A pipe pre-loaded with the script; closing the write end signals EOF once
    # the bytes are consumed.
    read_fd, write_fd = os.pipe()
    os.write(write_fd, script)
    os.close(write_fd)

    transport = Transport.__new__(Transport)
    transport._buf = b""
    transport.last_header = []
    transport._command_timeout = 2.0
    transport._event_timeout = 2.0

    class _Proc:
        stdout = _Stdout(read_fd)
        stdin = _Stdin()

        def poll(self) -> None:
            return None

    transport.proc = _Proc()
    return transport


def testCommandDrainsAPendingAsyncEventBeforeTheReply() -> None:
    """A breakpoint event queued ahead of a reply is kept, and the data is clean.

    This is the #1/#2 fix: the leftover prompt of an async event no longer
    leaves the next command reading a bare or prompt-prefixed line.
    """

    pending = "* BRK BREAKPOINT 00 0500\n1: [ 00:0500 a9 aa lda ]\n\nx16db > "
    reply = (
        "mode=c02 pc=0500 a=00 b=00 c=0000 x=0001 y=0008 sp=01ee p=32 "
        "k=00 db=00 dp=0000 e=1 ram=01 rom=00\nRDY\n1: [ 00:0500 a9 aa lda ]\n\nx16db > "
    )
    transport = _transportFeeding((pending + reply).encode())

    response = transport.command("reg")
    transport.proc.stdout.close()

    # The reply data is the register line, with no prompt leaked into it.
    assert response.terminator == "RDY"
    assert response.data == [
        "mode=c02 pc=0500 a=00 b=00 c=0000 x=0001 y=0008 sp=01ee p=32 "
        "k=00 db=00 dp=0000 e=1 ram=01 rom=00"
    ]
    assert all("x16db" not in line for line in response.data)

    # The event that was queued ahead of the reply is captured, not dropped.
    assert response.events == ["* BRK BREAKPOINT 00 0500"]


def testCommandSkipsABareLeftoverPrompt() -> None:
    """A stray prompt ahead of a reply is skipped, not read as an empty response.

    This is the #1 signature: before the fix the command read just the bare
    prompt and raised "prompt without RDY or ERR".
    """

    script = "x16db > " + "stop\nRDY\n1: [ 00:0500 a9 aa lda ]\n\nx16db > "
    transport = _transportFeeding(script.encode())

    response = transport.command("mod")
    transport.proc.stdout.close()

    assert response.terminator == "RDY"
    assert response.data == ["stop"]


def testInterleavedPromptDoesNotLeakIntoData() -> None:
    """A resume's reply and a following event are split into two clean responses.

    The cnt reply and the async break each carry their own prompt. The command
    reads only the reply (no phantom "x16db > " data line), and the break is
    read next, which is what keeps run_until reliable (#4).
    """

    cnt = "RDY\n* RES\n1: [ 00:0500 a9 aa lda ]\n\nx16db > "
    brk = "* BRK BREAKPOINT 00 0500\n1: [ 00:0500 a9 aa lda ]\n\nx16db > "
    transport = _transportFeeding((cnt + brk).encode())

    first = transport.command("cnt")

    # The reply terminates at its own prompt, carries its own event, and no
    # mid-stream prompt has leaked into the data.
    assert first.terminator == "RDY"
    assert first.events == ["* RES"]
    assert all("x16db" not in line for line in first.data)

    # The break that followed is read as the next response, intact.
    second = transport.waitPrompt()
    transport.proc.stdout.close()
    assert second.events == ["* BRK BREAKPOINT 00 0500"]

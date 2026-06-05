# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Disassembly commands against the live emulator.

Disassemble a short known routine and confirm one returned line per
instruction, naming the address and mnemonic, with no trailing whitespace.
"""

from __future__ import annotations

from x16dbg.client import Client


def testDisassembleReturnsInstructionLines(client: Client) -> None:
    """Disassembling two NOPs returns one trimmed line each, naming the opcode.

    Args:
        client: the connected client fixture.
    """

    client.brk()
    client.transport.command("wmm 00 0500 ea ea")

    lines = client.disassemble(0x00, 0x0500, 2)

    assert len(lines) == 2
    assert "0500" in lines[0]
    assert "nop" in lines[0].lower()
    assert lines[0] == lines[0].rstrip()

# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""Typed results parsed from the debugger's line output.

The transport returns raw lines; this module turns the ones the client cares
about into dataclasses, so callers work with parsed values rather than strings.
Each type carries the parser for its own wire form as a classmethod, and the
forms here are taken from the live emulator, not the prose docs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from x16dbg.transport import X16dbgError, parseHex


class AccessType(str, Enum):
    """A memory access type, as named on the watchpoint wire form."""

    READ = "r"
    WRITE = "w"
    READWRITE = "rw"


class BreakReason(str, Enum):
    """Why the CPU entered STOP, as named on a BRK event."""

    USER = "USER"
    BREAKPOINT = "BREAKPOINT"
    STP = "STP"
    STEP = "STEP"


# * WP <id> <a> <bank>:<addr>=<val> pc=<bank>:<pc>
_WP_RE = re.compile(
    r"^\* WP (?P<id>\d+) (?P<access>[rw]) "
    r"(?P<bank>[0-9a-f]{2}):(?P<addr>[0-9a-f]{4})=(?P<val>[0-9a-f]{2}) "
    r"pc=(?P<pc_bank>[0-9a-f]{2}):(?P<pc>[0-9a-f]{4})$"
)

# * BRK <reason> <bank> <addr>
_BRK_RE = re.compile(
    r"^\* BRK (?P<reason>USER|BREAKPOINT|STP|STEP) (?P<bank>[0-9a-f]{2}) (?P<addr>[0-9a-f]{4})$"
)

# A memory dump row: 4-hex address, single-space hex bytes, two spaces, ASCII.
_MEM_ROW_RE = re.compile(r"^(?P<addr>[0-9a-f]{4}): (?P<hex>[0-9a-f ]*?)  (?P<ascii>.*)$")


@dataclass
class WatchHit:
    """A watchpoint hit, naming the access and the instruction that made it.

    Attributes:
        id: the watchpoint's slot id.
        access: whether the access was a read or a write.
        bank: the bank of the watched location.
        addr: the watched address.
        val: the byte value read or written.
        pc_bank: the bank of the instruction that made the access.
        pc: the program counter of that instruction.
    """

    id: int
    access: AccessType
    bank: int
    addr: int
    val: int
    pc_bank: int
    pc: int

    @classmethod
    def parse(cls, line: str) -> WatchHit:
        """Parse a "* WP ..." event line.

        Args:
            line: the event line from the emulator.

        Returns:
            WatchHit: the parsed hit.

        Raises:
            X16dbgError: when the line is not a watchpoint event.
        """

        match = _WP_RE.match(line)

        if match is None:
            raise X16dbgError(f"not a watchpoint event: {line!r}")

        hit = cls(
            id=int(match["id"]),
            access=AccessType(match["access"]),
            bank=parseHex(match["bank"]),
            addr=parseHex(match["addr"]),
            val=parseHex(match["val"]),
            pc_bank=parseHex(match["pc_bank"]),
            pc=parseHex(match["pc"]),
        )
        return hit


@dataclass
class BreakEvent:
    """A break into STOP, naming the reason and where the CPU stopped.

    Attributes:
        reason: why the CPU stopped.
        bank: the bank the CPU stopped in.
        addr: the address the CPU stopped at.
    """

    reason: BreakReason
    bank: int
    addr: int

    @classmethod
    def parse(cls, line: str) -> BreakEvent:
        """Parse a "* BRK ..." event line.

        Args:
            line: the event line from the emulator.

        Returns:
            BreakEvent: the parsed break.

        Raises:
            X16dbgError: when the line is not a break event.
        """

        match = _BRK_RE.match(line)

        if match is None:
            raise X16dbgError(f"not a break event: {line!r}")

        event = cls(
            reason=BreakReason(match["reason"]),
            bank=parseHex(match["bank"]),
            addr=parseHex(match["addr"]),
        )
        return event


@dataclass
class Registers:
    """The CPU register snapshot from a reg dump.

    The 65C816-only registers are present on a 65C02 build too, where their
    values are not architecturally meaningful; mode says which set applies.
    """

    mode: str  # CPU mode: "c02" (65C02) or "c816" (65C816)
    pc: int  # program counter
    a: int  # accumulator (the low 8 bits of C on the 65C816)
    b: int  # high byte of the 16-bit accumulator (65C816)
    c: int  # full 16-bit accumulator, B:A (65C816)
    x: int  # X index register
    y: int  # Y index register
    sp: int  # stack pointer
    p: int  # processor status flags (NV-BDIZC)
    k: int  # program bank register (65C816)
    db: int  # data bank register (65C816)
    dp: int  # direct page register (65C816)
    e: int  # emulation-mode flag, 1 in 6502 emulation (65C816)
    ram: int  # currently selected RAM bank
    rom: int  # currently selected ROM bank

    @classmethod
    def parse(cls, line: str) -> Registers:
        """Parse a reg dump line of space-separated key=value fields.

        Args:
            line: the single-line reg output.

        Returns:
            Registers: the parsed snapshot.

        Raises:
            X16dbgError: when a field is missing or malformed.
        """

        # Split "k=v k=v ..." into a lookup, tolerating no surprises in spacing.
        fields = {}

        for token in line.split():
            if "=" not in token:
                raise X16dbgError(f"malformed reg field: {token!r} in {line!r}")

            key, value = token.split("=", 1)
            fields[key] = value

        try:
            snapshot = cls(
                mode=fields["mode"],
                pc=parseHex(fields["pc"]),
                a=parseHex(fields["a"]),
                b=parseHex(fields["b"]),
                c=parseHex(fields["c"]),
                x=parseHex(fields["x"]),
                y=parseHex(fields["y"]),
                sp=parseHex(fields["sp"]),
                p=parseHex(fields["p"]),
                k=parseHex(fields["k"]),
                db=parseHex(fields["db"]),
                dp=parseHex(fields["dp"]),
                e=parseHex(fields["e"]),
                ram=parseHex(fields["ram"]),
                rom=parseHex(fields["rom"]),
            )

        except KeyError as missing:
            raise X16dbgError(f"reg dump missing field {missing}: {line!r}") from missing

        return snapshot


@dataclass
class MemoryRow:
    """One row of a memory dump: a start address and its bytes.

    Attributes:
        addr: the address of the first byte in the row.
        data: the bytes on the row.
    """

    addr: int
    data: bytes

    @classmethod
    def parse(cls, line: str) -> MemoryRow:
        """Parse a memory dump row.

        Args:
            line: a dump row such as "0400: de ad be ef ...  ....".

        Returns:
            MemoryRow: the address and bytes from the row.

        Raises:
            X16dbgError: when the line is not a dump row.
        """

        match = _MEM_ROW_RE.match(line)

        if match is None:
            raise X16dbgError(f"not a memory row: {line!r}")

        addr = parseHex(match["addr"])
        data = bytes(parseHex(token) for token in match["hex"].split())
        row = cls(addr=addr, data=data)
        return row


@dataclass
class MemoryDump:
    """A contiguous memory read, as one or more rows.

    Attributes:
        rows: the dump rows in order.
    """

    rows: list[MemoryRow]

    @property
    def start(self) -> int:
        """The address of the first byte in the dump.

        Returns:
            int: the start address.
        """

        addr = self.rows[0].addr
        return addr

    @property
    def data(self) -> bytes:
        """The dump's bytes, concatenated across rows.

        Returns:
            bytes: every byte of the dump in order.
        """

        joined = b"".join(row.data for row in self.rows)
        return joined

    @classmethod
    def parse(cls, lines: list[str]) -> MemoryDump:
        """Parse the data lines of a mem command into a dump.

        Args:
            lines: the data lines returned by mem.

        Returns:
            MemoryDump: the parsed rows.
        """

        rows = [MemoryRow.parse(line) for line in lines]
        dump = cls(rows=rows)
        return dump

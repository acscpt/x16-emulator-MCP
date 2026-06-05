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

# An lwp listing row, less any trailing " off": id, access, bank:addr, an
# optional "-end" range, the hit count, and an optional " if <cond>".
_WP_LIST_RE = re.compile(
    r"^(?P<id>\d+): (?P<access>rw|r|w) "
    r"(?P<bank>[0-9a-f]{2}):(?P<addr>[0-9a-f]{4})(?:-(?P<end>[0-9a-f]{4}))? "
    r"hits=(?P<hits>\d+)(?: if (?P<condition>.+))?$"
)

# * BRK <reason> <bank> <addr>
_BRK_RE = re.compile(
    r"^\* BRK (?P<reason>USER|BREAKPOINT|STP|STEP) (?P<bank>[0-9a-f]{2}) (?P<addr>[0-9a-f]{4})$"
)

# An lbp listing row: "<bank>: <addr>", with an optional "  if <cond>" tail.
_BP_RE = re.compile(r"^(?P<bank>[0-9a-f]{2}): (?P<addr>[0-9a-f]{4})(?:  if (?P<condition>.+))?$")

# A memory dump row: a 4-hex (RAM) or 5-hex (17-bit VRAM) address, single-space
# hex bytes, two spaces, then the ASCII column.
_MEM_ROW_RE = re.compile(r"^(?P<addr>[0-9a-f]{4,5}): (?P<hex>[0-9a-f ]*?)  (?P<ascii>.*)$")

# A stack row from stk: "<addr>: <value>", both hex.
_STK_RE = re.compile(r"^(?P<addr>[0-9a-f]{4}): (?P<value>[0-9a-f]{2})$")


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class Watchpoint:
    """An armed watchpoint, as listed by lwp.

    Watchpoints are addressed by a stable slot id, where breakpoints are keyed
    by location: a watchpoint covers a range that can overlap or repeat another,
    so the address alone would not identify it.

    Attributes:
        id: the slot id, stable until the watchpoint is cleared.
        access: whether it watches reads, writes, or both.
        bank: the bank of the watched location; 0 for unbanked low memory.
        addr: the watched address, or the start of a watched range.
        hits: the running count of times the watchpoint has fired.
        end: the inclusive end of the range, or None for a single byte.
        enabled: False when the watchpoint is muted with wp <id> off.
        condition: the verbatim if-clause, or None when unconditional.
    """

    id: int
    access: AccessType
    bank: int
    addr: int
    hits: int
    end: int | None = None
    enabled: bool = True
    condition: str | None = None

    @classmethod
    def parse(cls, line: str) -> Watchpoint:
        """Parse one lwp listing row.

        Args:
            line: a row such as "0: w 00:0070 hits=0" or
                "1: rw 00:0080-008f hits=3 if val != $00 off".

        Returns:
            Watchpoint: the parsed watchpoint.

        Raises:
            X16dbgError: when the line is not a watchpoint listing row.
        """

        # The disabled flag, when set, is the final " off" the emulator appends
        # after any condition; peel it off before matching the rest of the row.
        enabled = True
        body = line

        if body.endswith(" off"):
            enabled = False
            body = body[: -len(" off")]

        match = _WP_LIST_RE.match(body)

        if match is None:
            raise X16dbgError(f"not a watchpoint row: {line!r}")

        # The range end is present only for a multi-byte watchpoint.
        end = parseHex(match["end"]) if match["end"] is not None else None

        watchpoint = cls(
            id=int(match["id"]),
            access=AccessType(match["access"]),
            bank=parseHex(match["bank"]),
            addr=parseHex(match["addr"]),
            hits=int(match["hits"]),
            end=end,
            enabled=enabled,
            condition=match["condition"],
        )
        return watchpoint


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class Breakpoint:
    """A user breakpoint, as listed by lbp.

    Breakpoints are identified by location rather than by a slot id, so there is
    at most one per location. The condition, when present, is the verbatim
    if-clause the break stops on.

    Attributes:
        bank: the program (K) bank from the listing; 0 on a 65C02. This is the
            execution bank lbp reports, not the X16 RAM/ROM bank passed when
            arming a banked breakpoint, which lbp does not surface.
        addr: the address execution stops at.
        enabled: False when the breakpoint is muted with bp <bank> <addr> off.
        condition: the if-clause expression, or None when unconditional.
    """

    bank: int
    addr: int
    enabled: bool = True
    condition: str | None = None

    @classmethod
    def parse(cls, line: str) -> Breakpoint:
        """Parse one lbp listing row.

        Args:
            line: a row such as "00: c010", "00: c04f  if a == $ff", or a
                disabled row ending in " off".

        Returns:
            Breakpoint: the parsed breakpoint.

        Raises:
            X16dbgError: when the line is not a breakpoint listing row.
        """

        # A disabled breakpoint ends with " off", appended after any condition;
        # peel it off before matching the rest of the row.
        enabled = True
        body = line

        if body.endswith(" off"):
            enabled = False
            body = body[: -len(" off")]

        match = _BP_RE.match(body)

        if match is None:
            raise X16dbgError(f"not a breakpoint row: {line!r}")

        # The condition group is None on a plain row and the verbatim
        # expression (minus the "  if " lead) on a conditional one.
        parsed = cls(
            bank=parseHex(match["bank"]),
            addr=parseHex(match["addr"]),
            enabled=enabled,
            condition=match["condition"],
        )
        return parsed


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class MemoryDump:
    """A contiguous memory read, as one or more rows.

    Attributes:
        rows: the dump rows in order.
    """

    # A tuple, not a list: a dump is a fixed snapshot, so its rows never change
    # after parsing, and an immutable field keeps this frozen dataclass hashable
    # (a list field is unhashable, so hashing the dump would raise TypeError).
    rows: tuple[MemoryRow, ...]

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

        rows = tuple(MemoryRow.parse(line) for line in lines)
        dump = cls(rows=rows)
        return dump


@dataclass(frozen=True)
class StackEntry:
    """One byte of the 6502 stack, with the address it occupies.

    Attributes:
        addr: the stack address, in page 1.
        value: the byte stored there.
    """

    addr: int
    value: int

    @classmethod
    def parse(cls, line: str) -> StackEntry:
        """Parse a stk row of the form "<addr>: <value>".

        Args:
            line: a row such as "01fe: 12".

        Returns:
            StackEntry: the parsed entry.

        Raises:
            X16dbgError: when the line is not a stack row.
        """

        match = _STK_RE.match(line)

        if match is None:
            raise X16dbgError(f"not a stack row: {line!r}")

        entry = cls(addr=parseHex(match["addr"]), value=parseHex(match["value"]))
        return entry


@dataclass(frozen=True)
class VeraState:
    """A snapshot of VERA's internal state, from vrg.

    This is the video chip's register state, not a dump of VRAM. Every field is
    parsed from the fixed key=value line into an integer.
    """

    addr0: int  # data port 0 address pointer (17-bit)
    addr1: int  # data port 1 address pointer (17-bit)
    data0: int  # data port 0 latch
    data1: int  # data port 1 latch
    ctrl: int  # control register
    video: int  # video mode / output register
    hscale: int  # horizontal scale
    vscale: int  # vertical scale
    fxctl: int  # FX engine control
    fxmul: int  # FX multiplier
    cache: int  # FX cache (32-bit)
    accum: int  # FX accumulator (32-bit)

    @classmethod
    def parse(cls, line: str) -> VeraState:
        """Parse the vrg line of space-separated key=value fields.

        Args:
            line: the single-line vrg output.

        Returns:
            VeraState: the parsed snapshot.

        Raises:
            X16dbgError: when a field is missing or malformed.
        """

        # Split "k=v k=v ..." into a lookup, the same shape as the reg dump.
        fields = {}

        for token in line.split():
            if "=" not in token:
                raise X16dbgError(f"malformed vrg field: {token!r} in {line!r}")

            key, value = token.split("=", 1)
            fields[key] = value

        try:
            state = cls(
                addr0=parseHex(fields["addr0"]),
                addr1=parseHex(fields["addr1"]),
                data0=parseHex(fields["data0"]),
                data1=parseHex(fields["data1"]),
                ctrl=parseHex(fields["ctrl"]),
                video=parseHex(fields["video"]),
                hscale=parseHex(fields["hscale"]),
                vscale=parseHex(fields["vscale"]),
                fxctl=parseHex(fields["fxctl"]),
                fxmul=parseHex(fields["fxmul"]),
                cache=parseHex(fields["cache"]),
                accum=parseHex(fields["accum"]),
            )

        except KeyError as missing:
            raise X16dbgError(f"vrg snapshot missing field {missing}: {line!r}") from missing

        return state

# Result types

The reads return frozen dataclasses, parsed from the wire forms taken from the live emulator. All are re-exported from the package top. Being frozen, they are immutable and hashable.

## `Registers`

The CPU register snapshot. `mode` is `"c02"` or `"c816"`; the 65C816 registers (`b`, `c`, `k`, `db`, `dp`, `e`) are present on a 65C02 build but not meaningful there.

Fields: `mode` *(str)*, `pc`, `a`, `b`, `c`, `x`, `y`, `sp`, `p`, `k`, `db`, `dp`, `e`, `ram`, `rom` *(int)*.

## `WatchHit`

A watchpoint hit. Fields: `id` *(int)* slot, `access` *(AccessType)*, `bank`, `addr`, `val` *(int)* the byte accessed, `pc_bank`, `pc` *(int)* the instruction that made the access.

## `BreakEvent`

A break into STOP. Fields: `reason` *(BreakReason)*, `bank`, `addr` *(int)*.

## `Breakpoint`

An armed breakpoint, as listed. Fields: `bank` *(int)* the program bank from the listing, `addr` *(int)*, `enabled` *(bool)*, `condition` *(str or None)*.

## `Watchpoint`

An armed watchpoint, as listed. Fields: `id` *(int)*, `access` *(AccessType)*, `bank`, `addr` *(int)*, `hits` *(int)* the running fire count, `end` *(int or None)* the range end, `enabled` *(bool)*, `condition` *(str or None)*.

## `MemoryRow`

One dump row: `addr` *(int)* and `data` *(bytes)*.

## `MemoryDump`

A contiguous read. Holds `rows` *(tuple of MemoryRow)* and exposes `.start` *(int)*, the first address, and `.data` *(bytes)*, every byte concatenated in order.

## `StackEntry`

One stack byte: `addr` *(int)* in page 1, `value` *(int)*.

## `VeraState`

A VERA register snapshot. Fields *(int)*: `addr0`, `addr1`, `data0`, `data1`, `ctrl`, `video`, `hscale`, `vscale`, `fxctl`, `fxmul`, `cache`, `accum`.

## `AccessType`

A string enum for a watchpoint access: `READ` (`"r"`), `WRITE` (`"w"`), `READWRITE` (`"rw"`).

## `BreakReason`

A string enum for why the CPU stopped: `USER`, `BREAKPOINT`, `STP`, `STEP`.

[^ Index](../python-api.md#index)

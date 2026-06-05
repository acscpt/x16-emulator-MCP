# Inspection

These read machine state at the moment of the call and change nothing. While the CPU is running, the values are sampled at an instruction boundary and are slightly stale; for a precise reading, [`brk`](execution.md#brk) first.

---

## `clocks`

```python
clocks() -> int
```

The CPU cycles elapsed since the last resume. The counter rebases on every resume, so in STOP it reports the length of the just-finished run. This is the one count the protocol returns in decimal.

[^ Index](../python-api.md#index)

---

## `stack`

```python
stack(count=16) -> tuple[StackEntry, ...]
```

Read the top of the 6502 stack, most-recent push first, reading upward from one past the stack pointer. `count` is capped at `0x40`. Each entry carries its page-1 address and the byte stored there; see [`StackEntry`](result-types.md#stackentry).

[^ Index](../python-api.md#index)

---

## `zeroPageRegisters`

```python
zeroPageRegisters() -> tuple[int, ...]
```

Read the cc65 zero-page R0..R15 pseudo-registers as sixteen 16-bit words, indexed so element `i` is `R<i>`. These are the C-runtime registers cc65 and CMDR-DOS use.

**Example**

```python
r = x16.zeroPageRegisters()
print(f"R0=${r[0]:04x} R1=${r[1]:04x}")
```

[^ Index](../python-api.md#index)

---

## `veraState`

```python
veraState() -> VeraState
```

Read a snapshot of VERA's internal state: the two address pointers and data latches, the control and video registers, scaling, and the FX engine fields. This is the video chip's register state, not a dump of VRAM. See [`VeraState`](result-types.md#verastate).

[^ Index](../python-api.md#index)

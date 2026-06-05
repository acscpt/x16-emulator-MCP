# Execution

The CPU is always in one of three states: STOP (paused), RUN (free-running), or a transient STEP. A resume returns the prompt immediately and the CPU runs concurrently with later commands until something stops it. Because the emulator runs at warp, a breakpoint or watchpoint can emit its event in the same read as the resume's own prompt or on the following one; the resume methods collect from both, so the stopping event is not missed.

---

## `cont`

```python
cont() -> None
```

Resume the CPU from STOP. The prompt returns at once and the CPU runs on. To resume and wait for the next stop, use [`runUntil`](#rununtil) instead.

[^ Index](../python-api.md#index)

---

## `brk`

```python
brk() -> BreakEvent | None
```

Force the running CPU into STOP at the next instruction boundary, and return the resulting `BreakEvent` (reason `USER`). The event is also recorded as `last_event`.

[^ Index](../python-api.md#index)

---

## `step`

```python
step() -> BreakEvent | None
```

Single-step one instruction and return the `BreakEvent` (reason `STEP`) for the new program counter.

[^ Index](../python-api.md#index)

---

## `stepOver`

```python
stepOver(*, timeout=None) -> BreakEvent | None
```

Step over a call. For a `JSR`/`JSL`/`JML` the emulator runs the call and breaks at the return, so the completing event can arrive on a later prompt; the transport collects across that wait. For any other instruction it behaves like [`step`](#step).

**Parameters**

- `timeout` *(float or None)*: seconds to wait for the completing event, or the event default.

[^ Index](../python-api.md#index)

---

## `reset`

```python
reset() -> None
```

Reset the CPU and reload the program counter from the reset vector. RAM, VERA, and peripherals are left untouched. The machine stays in STOP.

[^ Index](../python-api.md#index)

---

## `runUntil`

```python
runUntil(*, timeout=None) -> WatchHit | BreakEvent | None
```

Resume the CPU and return the next stopping event: a `WatchHit` for a watchpoint, a `BreakEvent` for a breakpoint, the `STP` opcode, or another break. Returns `None` if nothing stops the CPU within the timeout. The returned event is recorded as `last_event`. This is the resume half of the corruption-hunt loop.

**Parameters**

- `timeout` *(float or None)*: seconds to wait for the stopping event, or the event default.

**Example**

```python
x16.setWatchpoint("w", 0x00, 0x70)
hit = x16.runUntil()
if hit is not None:
    print(f"write to ${hit.addr:04x} from ${hit.pc:04x}")
```

[^ Index](../python-api.md#index)

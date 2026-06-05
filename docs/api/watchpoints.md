# Watchpoints

A watchpoint stops the CPU when the running program reads or writes a watched location, and names the instruction that made the access. This is the corruption-hunt primitive. Watchpoints are managed by a stable slot id, because a watchpoint covers a range that can overlap or repeat another. Reads are far more frequent than writes, so a read watchpoint on a busy location fires often; a condition narrows it.

---

## `setWatchpoint`

```python
setWatchpoint(access, bank, addr, *, end=None, condition=None) -> int
```

Arm a watchpoint over a byte or a range, and return its assigned slot id. The table holds 16 watchpoints.

**Parameters**

- `access` *(AccessType or str)*: `"r"`, `"w"`, or `"rw"` (or the [`AccessType`](result-types.md#accesstype) enum) for reads, writes, or both.

- `bank` *(int)*: the bank of the watched location; `0x00` for unbanked low memory.

- `addr` *(int)*: the watched address, or the start of a range.

- `end` *(int or None)*: the inclusive end of a range, or `None` for a single byte.

- `condition` *(str or None)*: a condition expression, passed verbatim. The access under test is available as `val`, `addr`, `is_write`, `is_read`, so `val == $ff` stops only on the write that stores `$ff`.

**Returns**

The slot id, stable for the watchpoint's lifetime.

**Example**

```python
slot = x16.setWatchpoint("rw", 0x00, 0x0080, end=0x008F)   # watch a 16-byte struct
x16.setWatchpoint("w", 0x00, 0x70, condition="val == $ff") # only the sentinel write
```

[^ Index](../python-api.md#index)

---

## `clearWatchpoint`

```python
clearWatchpoint(which) -> None
```

Clear one watchpoint by slot id, or every watchpoint with `"*"`.

**Parameters**

- `which` *(int or str)*: the slot id, or `"*"` for all.

[^ Index](../python-api.md#index)

---

## `enableWatchpoint`

```python
enableWatchpoint(slot_id) -> None
```

Re-enable a disabled watchpoint.

**Errors**

- `X16dbgError` when the slot holds no watchpoint.

[^ Index](../python-api.md#index)

---

## `disableWatchpoint`

```python
disableWatchpoint(slot_id) -> None
```

Mute a watchpoint without removing it; its definition and hit count are kept. Muting one at a time is the natural way to bisect which of several watchpoints is the one firing.

**Errors**

- `X16dbgError` when the slot holds no watchpoint.

[^ Index](../python-api.md#index)

---

## `listWatchpoints`

```python
listWatchpoints() -> tuple[Watchpoint, ...]
```

List the armed watchpoints as typed results, empty when none are armed. See [`Watchpoint`](result-types.md#watchpoint) for the fields, including the running hit count.

[^ Index](../python-api.md#index)

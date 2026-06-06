# Watchpoint tools

A watchpoint stops the CPU when the running program reads or writes a watched location, and names the instruction that made the access. This is the corruption-hunt primitive. Watchpoints are managed by a stable slot id, since a watchpoint can cover a range that overlaps another. For the index and the common contract, see [the tool reference](../tool-reference.md).

---

## `set_watchpoint`

Arm a read/write watchpoint over a byte or a range, and return its slot id.

**Parameters**

- `session_id` *(string)*: the session to arm.
- `access` *(string)*: `"r"`, `"w"`, or `"rw"` for reads, writes, or both.
- `bank` *(int)*: the bank of the watched location; `0` for low memory.
- `addr` *(int)*: the watched address, or the start of a range.
- `end` *(int, optional)*: the inclusive end of a range.
- `condition` *(string, optional)*: a C-style if-clause; the access is available as `val`, `addr`, `is_write`, `is_read`.

**Returns**

`{"slot": <id>}`, stable for the watchpoint's lifetime.

**Example**

```json
set_watchpoint("7f3a...", "w", 0, 112)                       ->  {"slot": 0}
set_watchpoint("7f3a...", "w", 0, 112, condition="val == $ff") ->  {"slot": 1}
```

The first stops on any write to `$70` (112); the second only on the write that stores `$ff`.

[^ Index](../tool-reference.md#index)

---

## `clear_watchpoint`

Clear one watchpoint by slot id, or every watchpoint with `"*"`.

**Parameters**

- `session_id` *(string)*: the session to clear from.
- `which` *(int or string)*: the slot id, or `"*"` for all.

**Returns**

`{"ok": true}`.

**Example**

```json
clear_watchpoint("7f3a...", 0)    ->  {"ok": true}
clear_watchpoint("7f3a...", "*")  ->  {"ok": true}
```

[^ Index](../tool-reference.md#index)

---

## `enable_watchpoint`

Re-enable a disabled watchpoint.

**Parameters**

- `session_id` *(string)*: the session holding the watchpoint.
- `slot_id` *(int)*: the slot id of the watchpoint.

**Returns**

`{"ok": true}`. An error if the slot holds no watchpoint.

**Example**

```json
enable_watchpoint("7f3a...", 0)  ->  {"ok": true}
```

[^ Index](../tool-reference.md#index)

---

## `disable_watchpoint`

Mute a watchpoint without removing it; its definition and hit count are kept. Muting one at a time is the way to bisect which of several is the one firing.

**Parameters**

- `session_id` *(string)*: the session holding the watchpoint.
- `slot_id` *(int)*: the slot id of the watchpoint.

**Returns**

`{"ok": true}`. An error if the slot holds no watchpoint.

**Example**

```json
disable_watchpoint("7f3a...", 0)  ->  {"ok": true}
```

[^ Index](../tool-reference.md#index)

---

## `list_watchpoints`

List the armed watchpoints.

**Parameters**

- `session_id` *(string)*: the session to list.

**Returns**

`{"watchpoints": [...]}`, each `{"id", "access", "bank", "addr", "hits", "end", "enabled", "condition"}`.

**Example**

```json
list_watchpoints("7f3a...")
  ->  {"watchpoints": [{"id": 0, "access": "w", "bank": 0, "addr": 112, "hits": 3,
                        "end": null, "enabled": true, "condition": null}]}
```

The watchpoint on `$70` has fired three times.

[^ Index](../tool-reference.md#index)

# Breakpoint tools

A breakpoint stops the CPU when execution reaches an address. It is keyed by location, so there is at most one per address; below `$A000` the location is just the address, while in the `$A000-$FFFF` window it is bank-specific and fires only while that bank is mapped. For the index and the common contract, see [the tool reference](../tool-reference.md).

---

## `set_breakpoint`

Arm a breakpoint at a bank and address, optionally conditional. Re-arming a location already set replaces it, updating or clearing the condition.

**Parameters**

- `session_id` *(string)*: the session to arm.
- `bank` *(int)*: the X16 RAM/ROM bank, used only for `$A000-$FFFF`; pass `0` for low memory.
- `addr` *(int)*: the address to stop at.
- `condition` *(string, optional)*: a C-style if-clause, hex needing a `$` or `0x` prefix.

**Returns**

`{"ok": true}`.

**Example**

```json
set_breakpoint("7f3a...", 0, 49232)                       ->  {"ok": true}
set_breakpoint("7f3a...", 0, 49231, condition="a == $ff") ->  {"ok": true}
```

The first breaks at `$C050` (49232) every pass; the second breaks at `$C04F` only when the accumulator holds `$ff`.

[^ Index](../tool-reference.md#index)

---

## `clear_breakpoint`

Clear the breakpoint at a bank and address.

**Parameters**

- `session_id` *(string)*: the session to clear from.
- `bank` *(int)*: the bank of the breakpoint.
- `addr` *(int)*: the address of the breakpoint.

**Returns**

`{"ok": true}`. An error if no breakpoint is set there.

**Example**

```json
clear_breakpoint("7f3a...", 0, 49232)  ->  {"ok": true}
```

[^ Index](../tool-reference.md#index)

---

## `clear_all_breakpoints`

Clear every breakpoint.

**Parameters**

- `session_id` *(string)*: the session to clear.

**Returns**

`{"ok": true}`.

**Example**

```json
clear_all_breakpoints("7f3a...")  ->  {"ok": true}
```

[^ Index](../tool-reference.md#index)

---

## `enable_breakpoint`

Re-enable a disabled breakpoint so it stops the CPU again.

**Parameters**

- `session_id` *(string)*: the session holding the breakpoint.
- `bank` *(int)*: the bank of the breakpoint.
- `addr` *(int)*: the address of the breakpoint.

**Returns**

`{"ok": true}`. An error if no breakpoint is set there.

**Example**

```json
enable_breakpoint("7f3a...", 0, 49232)  ->  {"ok": true}
```

[^ Index](../tool-reference.md#index)

---

## `disable_breakpoint`

Mute a breakpoint without removing it; it keeps its condition and shows as disabled in [`list_breakpoints`](#list_breakpoints).

**Parameters**

- `session_id` *(string)*: the session holding the breakpoint.
- `bank` *(int)*: the bank of the breakpoint.
- `addr` *(int)*: the address of the breakpoint.

**Returns**

`{"ok": true}`. An error if no breakpoint is set there.

**Example**

```json
disable_breakpoint("7f3a...", 0, 49232)  ->  {"ok": true}
```

[^ Index](../tool-reference.md#index)

---

## `list_breakpoints`

List the armed breakpoints, in the order they were added.

**Parameters**

- `session_id` *(string)*: the session to list.

**Returns**

`{"breakpoints": [...]}`, each `{"bank", "addr", "enabled", "condition"}`. The `bank` is the program bank from the listing, not the X16 bank a banked breakpoint was armed with.

**Example**

```json
list_breakpoints("7f3a...")
  ->  {"breakpoints": [{"bank": 0, "addr": 49232, "enabled": true, "condition": null},
                       {"bank": 0, "addr": 49231, "enabled": false, "condition": "a == $ff"}]}
```

[^ Index](../tool-reference.md#index)

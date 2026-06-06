# Session tools

The debugger is a window onto the machine's internal state, and it keeps a session of its own around that view. These tools report on that session, the current mode and a full snapshot, and control the header lines the emulator prints before each prompt. For the index and the common contract, see [the tool reference](../tool-reference.md).

---

## `mode`

Report the current machine mode.

**Parameters**

- `session_id` *(string)*: the session to query.

**Returns**

`{"mode": <m>}` where `m` is `"stop"`, `"run"`, or `"step"`.

**Example**

```json
mode("7f3a...")  ->  {"mode": "stop"}
```

[^ Index](../tool-reference.md#index)

---

## `state`

Read the full debugger state snapshot as labeled rows: the mode, the view cursor, the CPU program counter, the clock, and any breakpoints (with their X16 bank). The rows are returned verbatim, since the snapshot is formatted for reading rather than parsing.

**Parameters**

- `session_id` *(string)*: the session to read.

**Returns**

`{"state": [...]}`, the snapshot rows.

**Example**

```json
state("7f3a...")
  ->  {"state": ["mode      stop", "view_pc   00:c012  x16bank=-1",
                 "regs.pc   00:c012", "clk       14502", "bp        (none)"]}
```

[^ Index](../tool-reference.md#index)

---

## `set_headers`

Show or suppress all per-prompt header lines. The server already separates header lines from command data, so this is a convenience, not a requirement for clean output.

**Parameters**

- `session_id` *(string)*: the session to configure.
- `on` *(bool)*: true to show the header lines, false to suppress them.

**Returns**

`{"ok": true}`.

**Example**

```json
set_headers("7f3a...", false)  ->  {"ok": true}
```

[^ Index](../tool-reference.md#index)

---

## `set_header_line`

Show or suppress one header line.

**Parameters**

- `session_id` *(string)*: the session to configure.
- `line` *(string or int)*: the header line, by name (`cpu`, `aux`, `view`, `bp`) or number (`1`-`4`).
- `on` *(bool)*: true to show the line, false to suppress it.

**Returns**

`{"ok": true}`.

**Example**

```json
set_header_line("7f3a...", "cpu", true)  ->  {"ok": true}
```

[^ Index](../tool-reference.md#index)

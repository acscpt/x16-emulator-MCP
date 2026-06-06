# Execution tools

The CPU is in STOP (paused), RUN (free-running), or a transient STEP. These tools move it between those states. `run_until` is the one to reach for in a hunt: it resumes and reports the next thing that stops the CPU. For the index and the common contract, see [the tool reference](../tool-reference.md).

A stopping event comes back tagged. A watchpoint hit is `{"event": "watchpoint", ...}` with the access and the program counter; a break is `{"event": "break", "reason": ...}`; nothing within the timeout is `{"event": null}`.

---

## `continue`

Resume the CPU from STOP. The call returns at once and the CPU runs on; to resume and wait for the next stop, use [`run_until`](#run_until).

**Parameters**

- `session_id` *(string)*: the session to resume.

**Returns**

`{"ok": true}`.

**Example**

```json
continue("7f3a...")  ->  {"ok": true}
```

[^ Index](../tool-reference.md#index)

---

## `break`

Force the running CPU into STOP and report the resulting break.

**Parameters**

- `session_id` *(string)*: the session to halt.

**Returns**

A `break` event with reason `USER`.

**Example**

```json
break("7f3a...")  ->  {"event": "break", "reason": "USER", "bank": 0, "addr": 49170}
```

The CPU stopped at `$C012` (49170), the instruction it was about to run.

[^ Index](../tool-reference.md#index)

---

## `step`

Single-step one instruction and report the break.

**Parameters**

- `session_id` *(string)*: the session to step.

**Returns**

A `break` event with reason `STEP`.

**Example**

```json
step("7f3a...")  ->  {"event": "break", "reason": "STEP", "bank": 0, "addr": 1283}
```

After stepping the three-byte `lda $0200` at `$0500`, the PC lands on `$0503` (1283).

[^ Index](../tool-reference.md#index)

---

## `step_over`

Step over a call. For a `JSR`/`JSL`/`JML` the emulator runs the call and breaks at the return; for anything else it behaves like [`step`](#step).

**Parameters**

- `session_id` *(string)*: the session to step.
- `timeout` *(float, optional)*: seconds to wait for the call to return.

**Returns**

A `break` event with reason `STEP`, at the instruction after the call.

**Example**

```json
step_over("7f3a...")  ->  {"event": "break", "reason": "STEP", "bank": 0, "addr": 1283}
```

[^ Index](../tool-reference.md#index)

---

## `reset`

Reset the CPU and reload the program counter from the reset vector. RAM, VERA, and peripherals are left untouched, and the machine stays in STOP.

**Parameters**

- `session_id` *(string)*: the session to reset.

**Returns**

`{"ok": true}`.

**Example**

```json
reset("7f3a...")  ->  {"ok": true}
```

[^ Index](../tool-reference.md#index)

---

## `run_until`

Resume the CPU and return the next stopping event. With a watchpoint armed, this is the resume half of the corruption-hunt loop.

**Parameters**

- `session_id` *(string)*: the session to resume.
- `timeout` *(float, optional)*: seconds to wait for the stop.

**Returns**

A tagged `watchpoint` or `break` event, or `{"event": null}` if nothing stopped within the timeout.

**Example**

```json
run_until("7f3a...")
  ->  {"event": "watchpoint", "id": 0, "access": "w",
       "bank": 0, "addr": 112, "val": 170, "pc_bank": 0, "pc": 1282}
```

The write watchpoint on `$70` (112) fired: `$aa` (170) was stored by the instruction at `$0502` (1282).

[^ Index](../tool-reference.md#index)

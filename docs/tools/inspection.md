# Inspection tools

These report machine state at the moment of the call and change nothing: the cycle counter, the top of the stack, the cc65 zero-page registers, and VERA's state. While the CPU runs, the values are sampled at an instruction boundary and are slightly stale; for a precise reading, [`break`](execution.md#break) first. For the index and the common contract, see [the tool reference](../tool-reference.md).

---

## `clocks`

Report the CPU cycles elapsed since the last resume. The counter rebases on every resume, so in STOP it reports the length of the just-finished run.

**Parameters**

- `session_id` *(string)*: the session to query.

**Returns**

`{"clocks": <n>}`.

**Example**

```json
clocks("7f3a...")  ->  {"clocks": 14502}
```

[^ Index](../tool-reference.md#index)

---

## `stack`

Read the top of the 6502 stack, most-recent push first, reading upward from one past the stack pointer.

**Parameters**

- `session_id` *(string)*: the session to read.
- `count` *(int, default 16)*: the number of bytes (capped at `0x40`).

**Returns**

`{"stack": [...]}`, each entry `{"addr", "value"}`.

**Example**

```json
stack("7f3a...", 3)
  ->  {"stack": [{"addr": 510, "value": 18}, {"addr": 511, "value": 52},
                 {"addr": 256, "value": 0}]}
```

[^ Index](../tool-reference.md#index)

---

## `zero_page_registers`

Read the cc65 zero-page R0..R15 pseudo-registers, the C-runtime registers cc65 and CMDR-DOS use.

**Parameters**

- `session_id` *(string)*: the session to read.

**Returns**

`{"registers": [...]}`, sixteen 16-bit words indexed so element `i` is R`i`.

**Example**

```json
zero_page_registers("7f3a...")  ->  {"registers": [4660, 43981, 0, 0, 128, 0, ...]}
```

R0 holds `$1234` (4660), R1 holds `$abcd` (43981).

[^ Index](../tool-reference.md#index)

---

## `vera_state`

Read a snapshot of VERA's internal state: the two address pointers and data latches, the control and video registers, scaling, and the FX engine fields. This is the video chip's register state, not a dump of VRAM.

**Parameters**

- `session_id` *(string)*: the session to read.

**Returns**

The VERA fields: `addr0`, `addr1`, `data0`, `data1`, `ctrl`, `video`, `hscale`, `vscale`, `fxctl`, `fxmul`, `cache`, `accum`.

**Example**

```json
vera_state("7f3a...")
  ->  {"addr0": 49152, "addr1": 0, "data0": 255, "ctrl": 0, "video": 1,
       "hscale": 128, "vscale": 128, ...}
```

[^ Index](../tool-reference.md#index)

# Register tools

Read the CPU register snapshot, or set a single register by name. Reading is most telling just after a stop; setting `pc` is how a script repoints execution before a resume. For the index and the common contract, see [the tool reference](../tool-reference.md).

---

## `read_registers`

Read the CPU register snapshot.

**Parameters**

- `session_id` *(string)*: the session to read.

**Returns**

The register fields: `mode` (`"c02"` or `"c816"`), `pc`, `a`, `b`, `c`, `x`, `y`, `sp`, `p`, `k`, `db`, `dp`, `e`, `ram`, `rom`. The 65C816 registers appear on a 65C02 build too but are not meaningful there.

**Example**

```json
read_registers("7f3a...")
  ->  {"mode": "c02", "pc": 49170, "a": 7, "x": 0, "y": 0, "sp": 509,
       "p": 52, "ram": 0, "rom": 0, ...}
```

The CPU is stopped at `$C012` (49170) with `$07` in the accumulator and the stack pointer at `$01FD` (509).

[^ Index](../tool-reference.md#index)

---

## `set_register`

Set one CPU register. Setting `pc` does not resume the CPU; follow with [`continue`](execution.md#continue) to run from the new address.

**Parameters**

- `session_id` *(string)*: the session to modify.
- `name` *(string)*: one of `pc`, `a`, `b`, `c`, `x`, `y`, `sp`, `p`, `k`, `db`, `dp`, `e`.
- `value` *(int)*: the new value; the width is implied by the register.

**Returns**

`{"ok": true}`. An error if the register name is not recognised.

**Example**

```json
set_register("7f3a...", "pc", 1280)  ->  {"ok": true}
set_register("7f3a...", "a", 66)     ->  {"ok": true}
```

The program counter now points at `$0500` (1280) and the accumulator holds `$42` (66).

[^ Index](../tool-reference.md#index)

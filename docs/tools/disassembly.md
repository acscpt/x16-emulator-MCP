# Disassembly tools

Disassembly reads memory back as the 6502 (or 65C816) instructions stored there, the quick way to see what sits at a program counter. It reads from an explicit address without moving the debugger's view cursor. For the index and the common contract, see [the tool reference](../tool-reference.md).

---

## `disassemble`

Disassemble a number of instructions starting at an address.

**Parameters**

- `session_id` *(string)*: the session to disassemble.
- `bank` *(int)*: the CPU bank.
- `addr` *(int)*: the 16-bit start address.
- `count` *(int)*: the number of instructions (capped at `0x40`).

**Returns**

`{"lines": [...]}`, one verbatim disassembly line per instruction.

**Example**

```json
disassemble("7f3a...", 0, 49168, 3)
  ->  {"lines": ["00:c010 ad 00 02  lda $0200",
                 "00:c013 85 03     sta $03",
                 "00:c015 4c 30 c0  jmp $c030"]}
```

Three instructions from `$C010` (49168).

[^ Index](../tool-reference.md#index)

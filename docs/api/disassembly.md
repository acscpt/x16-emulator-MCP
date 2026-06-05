# Disassembly

Disassembly reads memory back as the 6502 (or 65C816) instructions stored there. The `disassemble` command decodes a given number of instructions from an explicit bank and address and returns them as text; because the address is explicit, it reads without moving the debugger's view cursor, so it fits a script that just wants the code at a program counter.

---

## `disassemble`

```python
disassemble(bank, addr, count) -> tuple[str, ...]
```

Disassemble `count` instructions (capped at `0x40`) and return one line each, trailing whitespace trimmed. The lines are returned verbatim: their layout of address, raw bytes, and a variable-width mnemonic is not stable enough to parse into fields safely.

**Example**

```python
for line in x16.disassemble(0x00, 0xC000, 4):
    print(line)
```

[^ Index](../python-api.md#index)

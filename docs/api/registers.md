# Registers

The register file is the CPU's live working state: the program counter, the accumulator and index registers, the stack pointer, the processor flags, and on a 65C816 a few more. Reading it is most telling just after a stop, when the values pin down where the CPU is and what it was holding. Writing a single register is the other half; setting `pc`, for instance, repoints execution before a resume, the usual way a script jumps the CPU somewhere new.

---

## `readRegisters`

```python
readRegisters() -> Registers
```

Read the CPU register snapshot: the program counter, A/X/Y, stack pointer, status flags, the 65C816 extras, and the selected RAM and ROM banks. See [`Registers`](result-types.md#registers).

**Example**

```python
regs = x16.readRegisters()
print(f"pc=${regs.pc:04x} a=${regs.a:02x} sp=${regs.sp:04x}")
```

[^ Index](../python-api.md#index)

---

## `setRegister`

```python
setRegister(name, value) -> None
```

Set one CPU register. Setting `pc` does not resume the CPU; follow with a resume to run from the new address.

**Parameters**

- `name` *(str)*: one of `pc`, `a`, `b`, `c`, `x`, `y`, `sp`, `p`, `k`, `db`, `dp`, `e`.

- `value` *(int)*: the new value; the emulator takes the width from the register.

**Errors**

- `X16dbgError` when the register name is not recognised.

[^ Index](../python-api.md#index)

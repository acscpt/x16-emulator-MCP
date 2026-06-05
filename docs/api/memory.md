# Memory

CPU memory commands take an explicit `bank` and address and do not move any view state. A `bank` applies in the banked windows (`$A000-$BFFF` for RAM, `$C000-$FFFF` for ROM); below `$A000` it is ignored, by convention `0x00`.

---

## `readMemory`

```python
readMemory(bank, addr, count) -> MemoryDump
```

Read a contiguous block of CPU RAM. `count` is capped at `0x1000` per call by the emulator.

**Returns**

A [`MemoryDump`](result-types.md#memorydump). Its `.data` gives the bytes concatenated across rows, `.start` the first address.

**Example**

```python
dump = x16.readMemory(0x00, 0x0400, 16)
print(dump.data.hex())
```

[^ Index](../python-api.md#index)

---

## `writeMemory`

```python
writeMemory(bank, addr, values) -> None
```

Write consecutive bytes straight to the RAM array, bypassing I/O side effects, so the I/O region can be poked without triggering peripherals.

**Parameters**

- `values` *(iterable of int)*: the bytes to write in order, such as a `list[int]` or `bytes`.

[^ Index](../python-api.md#index)

---

## `fill`

```python
fill(bank, addr, value, count=1) -> None
```

Fill a range with one byte through the CPU's write path, so an address in the I/O region triggers the same peripheral side effects a store instruction would. For direct RAM-array writes that bypass I/O, use [`writeMemory`](#writememory).

[^ Index](../python-api.md#index)

---

## `find`

```python
find(bank, start, length, pattern) -> tuple[int, ...]
```

Search a range of RAM for a byte pattern and return the start address of each match, empty when none match.

**Parameters**

- `length` *(int)*: the length of the search range in bytes.

- `pattern` *(iterable of int)*: the 1-to-16-byte pattern to find.

**Example**

```python
for addr in x16.find(0x00, 0x0000, 0x8000, [0xDE, 0xAD]):
    print(f"match at ${addr:04x}")
```

[^ Index](../python-api.md#index)

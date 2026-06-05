# VRAM

VRAM is VERA's own memory, a 17-bit space (`00000`-`1ffff`) holding the tiles, sprites, bitmaps, and palette the video chip draws from. It sits apart from the CPU's address map and carries no bank, so the commands here name a VRAM address directly. A read comes back as the same [`MemoryDump`](result-types.md#memorydump) used for CPU memory, addressed in VRAM space; a write goes straight to the buffer, leaving VERA's own address registers untouched.

---

## `readVram`

```python
readVram(addr, count) -> MemoryDump
```

Read a contiguous block of VRAM. `count` is capped at `0x1000` per call.

[^ Index](../python-api.md#index)

---

## `writeVram`

```python
writeVram(addr, values) -> None
```

Write consecutive bytes straight to the VRAM buffer, bypassing VERA's data-port mechanism, so its address registers are not advanced.

[^ Index](../python-api.md#index)

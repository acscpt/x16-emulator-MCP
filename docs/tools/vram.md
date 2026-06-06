# VRAM tools

VRAM is VERA's own memory, a 17-bit address space (`00000`-`1ffff`) holding the tiles, sprites, bitmaps, and palette the video chip draws from. It is separate from CPU memory and takes no bank. A read comes back in the same form as a CPU read. For the index and the common contract, see [the tool reference](../tool-reference.md).

---

## `read_vram`

Read a contiguous block of VRAM.

**Parameters**

- `session_id` *(string)*: the session to read.
- `addr` *(int)*: the 17-bit VRAM start address.
- `count` *(int)*: the number of bytes (capped at `0x1000`).

**Returns**

`{"start", "hex", "length"}`: the start address, the bytes as a lowercase hex string, and the byte count.

**Example**

```json
read_vram("7f3a...", 0, 4)  ->  {"start": 0, "hex": "112233ef", "length": 4}
```

[^ Index](../tool-reference.md#index)

---

## `write_vram`

Write bytes to VRAM, straight to the VRAM buffer, bypassing VERA's data-port mechanism so its address registers are not advanced.

**Parameters**

- `session_id` *(string)*: the session to write to.
- `addr` *(int)*: the 17-bit VRAM start address.
- `values` *(list of int)*: the bytes to write in order.

**Returns**

`{"ok": true}`.

**Example**

```json
write_vram("7f3a...", 0, [17, 34, 51])  ->  {"ok": true}
```

Writes `11 22 33` to the start of VRAM.

[^ Index](../tool-reference.md#index)

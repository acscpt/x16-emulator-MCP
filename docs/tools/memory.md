# Memory tools

Read and write CPU RAM with an explicit bank and address. A `bank` applies in the banked windows (`$A000-$BFFF` for RAM, `$C000-$FFFF` for ROM); below `$A000` it is ignored, by convention `0`. For the index and the common contract, see [the tool reference](../tool-reference.md).

---

## `read_memory`

Read a contiguous block of CPU RAM.

**Parameters**

- `session_id` *(string)*: the session to read.
- `bank` *(int)*: the CPU bank.
- `addr` *(int)*: the 16-bit start address.
- `count` *(int)*: the number of bytes (capped at `0x1000`).

**Returns**

`{"start", "hex", "length"}`: the start address, the bytes as a lowercase hex string, and the byte count.

**Example**

```json
read_memory("7f3a...", 0, 1024, 4)  ->  {"start": 1024, "hex": "deadbeef", "length": 4}
```

Four bytes at `$0400` (1024) read back as `de ad be ef`.

[^ Index](../tool-reference.md#index)

---

## `write_memory`

Write bytes to CPU RAM, straight to the RAM array, bypassing I/O side effects.

**Parameters**

- `session_id` *(string)*: the session to write to.
- `bank` *(int)*: the CPU bank.
- `addr` *(int)*: the 16-bit start address.
- `values` *(list of int)*: the bytes to write in order.

**Returns**

`{"ok": true}`.

**Example**

```json
write_memory("7f3a...", 0, 1280, [169, 170, 133, 112])  ->  {"ok": true}
```

That lays down `LDA #$aa ; STA $70` (`a9 aa 85 70`) at `$0500` (1280).

[^ Index](../tool-reference.md#index)

---

## `fill`

Fill a range of CPU RAM with a byte through the CPU's write path, so an address in the I/O region triggers the peripheral side effects a store would. For direct RAM writes that bypass I/O, use [`write_memory`](#write_memory).

**Parameters**

- `session_id` *(string)*: the session to write to.
- `bank` *(int)*: the CPU bank.
- `addr` *(int)*: the 16-bit start address.
- `value` *(int)*: the byte written at each position.
- `count` *(int, default 1)*: the number of bytes.

**Returns**

`{"ok": true}`.

**Example**

```json
fill("7f3a...", 0, 1792, 90, 8)  ->  {"ok": true}
```

Eight bytes at `$0700` (1792) are set to `$5a` (90).

[^ Index](../tool-reference.md#index)

---

## `find`

Search a range of CPU RAM for a byte pattern.

**Parameters**

- `session_id` *(string)*: the session to search.
- `bank` *(int)*: the CPU bank.
- `start` *(int)*: the 16-bit start of the range.
- `length` *(int)*: the length of the range in bytes.
- `pattern` *(list of int)*: the 1-to-16-byte pattern to find.

**Returns**

`{"matches": [...]}`, the start address of each match, empty when none match.

**Example**

```json
find("7f3a...", 0, 0, 4096, [222, 173])  ->  {"matches": [1024]}
```

The pattern `de ad` was found once, at `$0400` (1024).

[^ Index](../tool-reference.md#index)

# Capture

The X16 emulator renders the screen to an internal frame buffer on demand, even when running headless under `-debugstdio` with no window open. The command in this section captures that buffer as a PNG and returns the bytes.

---

## `screenshot`

```python
screenshot(path=None) -> bytes
```

Capture the current screen and return the PNG bytes. The emulator composes a frame from live VERA state on demand, so this works headless. With no path, a temporary file is used and removed once its bytes are read; a given path is written and left in place. The MCP layer wraps these bytes into an image block; the library hands back the raw PNG.

**Parameters**

- `path` *(path or None)*: where the emulator writes the PNG, or `None` for a temporary file.

**Example**

```python
png = x16.screenshot()
open("screen.png", "wb").write(png)
```

[^ Index](../python-api.md#index)

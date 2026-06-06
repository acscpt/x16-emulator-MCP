# Capture tools

The X16 emulator renders the screen to an internal frame buffer on demand, even when running headless under `-debugstdio` with no window open. This tool captures that buffer so the agent can see exactly what the machine is displaying. For the index and the common contract, see [the tool reference](../tool-reference.md).

---

## `screenshot`

Capture the current screen as a PNG image.

Unlike every other tool, this returns an MCP image block rather than a JSON object: the raw PNG the emulator composed, which an MCP client renders inline.

**Parameters**

- `session_id` *(string)*: the session to capture.

**Returns**

An image block carrying the PNG.

**Example**

```json
screenshot("7f3a...")  ->  <PNG image block>
```

[^ Index](../tool-reference.md#index)

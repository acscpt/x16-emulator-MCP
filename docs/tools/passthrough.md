# Passthrough

The typed tools are the primary, discoverable interface to the X16 debugger through this MCP server. The command below is a straight passthrough, to be used only when no typed tool covers what is needed, such as a rarely-used command or an experiment. For the index and the common contract, see [the tool reference](../tool-reference.md).

---

## `x16db`

Forward one raw line to the debugger and return its response.

The session-ending commands (`quit`, `qit`, `bail`) are refused by default, since they would kill the emulator out from under the session; end a session with [`close_session`](lifecycle.md#close_session). Pass `force` to allow them anyway, in which case the session is closed and dropped from the registry so the server's session list stays consistent.

**Parameters**

- `session_id` *(string)*: the session to drive.
- `command` *(string)*: the raw debugger command line.
- `force` *(bool, default false)*: allow the session-ending commands (`quit`, `qit`, `bail`).

**Returns**

`{"data", "events", "ended"}`: the response data lines, any asynchronous event lines, and whether the command ended the session.

**Example**

```json
x16db("7f3a...", "wmm 00 0500 a9 aa 85 70")
  ->  {"data": [], "events": [], "ended": false}
x16db("7f3a...", "mem 00 0500 04")
  ->  {"data": ["0500: a9 aa 85 70                                      ...p"],
       "events": [], "ended": false}
x16db("7f3a...", "quit", force=true)
  ->  {"data": [], "events": [], "ended": true}
```

The first writes four bytes; the second reads them back as a raw dump line; the third ends the session.

[^ Index](../tool-reference.md#index)

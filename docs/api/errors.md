# Errors

The following error exceptions can be raised from the API.

## `X16dbgError`

The base exception, covering a rejected command or a break in the protocol stream. Raised when:

- the debugger replies `ERR <message>`;
- a prompt arrives with no `RDY` or `ERR` terminator;
- a reply line cannot be parsed into its result type;
- the pipe to the emulator breaks, such as a broken pipe or an unexpected EOF.

## `X16ProtocolError`

A subclass of `X16dbgError`. Raised when:

- [`Client.launch`](lifecycle.md#clientlaunch) opens a session and the emulator reports a protocol version other than the one required.

## `TimeoutError`

The standard-library exception. Raised when:

- a command's prompt does not arrive within `command_timeout`;
- an event's prompt does not arrive within `event_timeout`.

[`runUntil`](execution.md#rununtil) and [`stepOver`](execution.md#stepover) absorb the event timeout and return `None` instead, so an awaited stop that never comes reads as "nothing stopped" rather than an exception.

```python
from x16dbg import X16dbgError

try:
    x16.clearBreakpoint(0x00, 0xC010)
except X16dbgError as exc:
    print("no breakpoint there:", exc)
```

[^ Index](../python-api.md#index)

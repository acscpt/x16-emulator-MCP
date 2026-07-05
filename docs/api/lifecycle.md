# Lifecycle

A session is one emulator subprocess, and a `Client` owns it from spawn to teardown. `Client.launch` starts the emulator headless, runs the startup handshake, gates on the protocol version, and returns a client ready for commands. Because the client is a context manager, a `with` block closes the subprocess on the way out, even if the work inside it raises.

---

## `Client.launch`

```python
Client.launch(emulator, rom, *, prg=None, load_addr=None, run=False,
              startup_bp=None, warp=True, fsroot=None, require_proto=2,
              command_timeout=2.0, event_timeout=5.0) -> Client
```

Spawn the emulator headless and return a connected client. This is the entry point; it builds the transport, runs the startup handshake, and gates on the protocol version, so the returned client is ready for commands.

**Parameters**

- `emulator`, `rom` *(path)*: the `x16emu` binary and `rom.bin`. Pass the results of `discoverEmulator()` and `discoverRom()`, or explicit paths.

- `prg` *(path or None)*: a PRG to load from the host filesystem at launch.

- `load_addr` *(int or None)*: an override load address for the PRG.

- `run` *(bool)*: when True, autostart the loaded program with BASIC RUN.

- `startup_bp` *(int or None)*: a hex address to break at on startup. With no startup breakpoint the CPU runs freely from reset.

- `warp` *(bool)*: when True (the default for an automated harness), remove the speed throttle so the CPU runs as fast as the host allows.

- `fsroot` *(path or None)*: a host directory the emulated machine uses as its disk, so a booted program's KERNAL `LOAD` reads real files from it over the device-8 passthrough. With none the emulator uses its own working directory. `discoverFsroot()` resolves it from the `X16FS_ROOT` environment variable.

- `require_proto` *(int or None)*: the protocol version to require; `None` skips the check.

- `command_timeout`, `event_timeout` *(float)*: seconds to wait for a command's prompt and for an asynchronous event prompt.

**Returns**

A connected `Client`, usable as a context manager.

**Errors**

- `X16ProtocolError` when the emulator reports a version other than `require_proto`.

**Example**

```python
from x16dbg import Client, discoverEmulator, discoverRom

with Client.launch(discoverEmulator(), discoverRom(), startup_bp=0xC000) as x16:
    print(x16.mode())   # stop
```

[^ Index](../python-api.md#index)

---

## `close`

```python
close() -> None
```

Ask the emulator to quit, wait for it, and kill it if it lingers. The context manager calls this on exit; call it directly when not using `with`. The client does not implement `__del__`, so an abandoned client without `close` leaves the subprocess running until it is killed.

[^ Index](../python-api.md#index)

---

## `protocolVersion`

```python
protocolVersion -> int | None
```

The protocol version the session reported at startup, or `None` when the check was skipped. A read-only property.

[^ Index](../python-api.md#index)

---

## Raw passthrough

Every typed method is a thin formatter over `client.transport.command(line)`, which sends one debugger line and returns a `Response` with its `data`, `events`, and `header`. It is the escape hatch for a command the library does not wrap yet, or for an experiment:

```python
response = x16.transport.command("hlp")
for line in response.data:
    print(line)
```

The typed methods are the primary interface, because they are discoverable and return parsed values. When a raw command gets used repeatedly for the same thing, that thing wants a typed method.

[^ Index](../python-api.md#index)

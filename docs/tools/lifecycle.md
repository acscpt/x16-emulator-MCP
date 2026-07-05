# Lifecycle tools

A session is one running emulator. These tools start one, stop it, swap the program it runs, and report the protocol it speaks. For the index and the common contract, see [the tool reference](../tool-reference.md).

---

## `create_session`

Boot an X16 emulator and return a session to drive.

**Parameters**

- `prg` *(string, optional)*: a PRG to boot; with none, a configured default is used if present, otherwise the machine boots to BASIC.
- `load_addr` *(int, optional)*: an override load address for the PRG.
- `run` *(bool, default true)*: autostart the loaded program.
- `startup_bp` *(int, optional)*: a hex address to break at on startup.

**Returns**

`{"session_id": "..."}`. The id is required by every other tool.

**Example**

```json
create_session()                      ->  {"session_id": "7f3a2c10-..."}
create_session(startup_bp=49152)      ->  {"session_id": "a91b..."}
```

The second call breaks at `$C000` (49152) as soon as the machine reaches it, handy for stopping before the program runs.

The machine's disk (device 8) is the host directory named by the server's `X16FS_ROOT` environment variable, so a booted program's KERNAL `LOAD` reads real files from it. This is a server-level setting shared by every session, configured once where the server is launched, not a per-call parameter; with it unset the emulator uses its own working directory. See [the installation guide](../installation.md#point-the-server-at-them).

[^ Index](../tool-reference.md#index)

---

## `close_session`

Close a session and stop its emulator subprocess.

**Parameters**

- `session_id` *(string)*: the session to close.

**Returns**

`{"ok": true}`.

**Example**

```json
close_session("7f3a...")  ->  {"ok": true}
```

[^ Index](../tool-reference.md#index)

---

## `boot_program`

Load a different program into a session by respawning its emulator.

The protocol is one subprocess per session, so switching the program means a fresh spawn; the session keeps its id. The emulator loads a PRG by typing LOAD at the BASIC prompt, so the program is present only after the machine has run: resume and let it boot, or set `startup_bp` at the program's entry on the next `create_session`, rather than reading memory the instant this returns. The respawn inherits the same `X16FS_ROOT` disk as `create_session`. For an in-session CPU reset that keeps the same program, use [`reset`](execution.md#reset).

**Parameters**

- `session_id` *(string)*: the session to respawn.
- `path` *(string)*: the PRG to load.
- `load_addr` *(int, optional)*: an override load address.
- `run` *(bool, default true)*: autostart the program.

**Returns**

`{"ok": true}`, once respawned.

**Example**

```json
boot_program("7f3a...", "/path/to/game.prg")  ->  {"ok": true}
```

[^ Index](../tool-reference.md#index)

---

## `protocol_version`

Report the debugger protocol version the session reported at startup.

**Parameters**

- `session_id` *(string)*: the session to query.

**Returns**

`{"protocol_version": <n>}`.

**Example**

```json
protocol_version("7f3a...")  ->  {"protocol_version": 2}
```

[^ Index](../tool-reference.md#index)

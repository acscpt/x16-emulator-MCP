# Tool reference

`x16mcp` is the MCP server: it exposes the Commander X16 debugger to an AI agent as a set of tools over stdio JSON-RPC. Each tool is a thin adapter onto one method of the `x16dbg` client harness, so the protocol mechanics, the warp-speed event race, and the typed parsing all live in the harness rather than here. For driving the debugger from Python directly, see [the Python API](python-api.md).

This page is the index and the common contract; each tool, with its parameters, return fields, and a worked example, is documented in its category page under [`tools/`](tools/). An agent's own view of a tool comes from the live schema served at runtime through `tools/list`; these pages are the human-facing reference behind it.

The server is built for one job above the rest: memory-corruption hunting. Arm a watchpoint on a byte that is being clobbered, run, and each hit names the program counter that wrote it. The [worked example](#worked-example-a-corruption-hunt) runs that loop through the tools end to end.

## Sessions

Every tool operates on a session, and a session is one running emulator. `create_session` boots an emulator and returns a `session_id`; every other tool takes that id as its first argument.

```json
create_session()  ->  {"session_id": "7f3a2c10-..."}
```

The model is deliberate: one server can hold several emulators at once, a buggy build and a fixed one side by side for instance, each addressed by its own id. A session lives until `close_session` ends it. `boot_program` swaps the program under test by respawning the emulator under the same id; because the emulator loads a PRG by typing LOAD at the BASIC prompt, the program is present only after the machine has run, so resume and let it boot rather than reading memory the instant `boot_program` returns. When the server shuts down it closes any session still open, so a dropped connection leaves no emulator running.

## Conventions

- **Every tool returns a JSON object.** A read puts its data in a named field (`read_registers` returns the register fields, `read_memory` returns `{"start", "hex", "length"}`, `list_watchpoints` returns `{"watchpoints": [...]}`); an action returns `{"ok": true}`. The one exception is `screenshot`, which returns an image block.

- **Numbers are integers, decimal in JSON.** Addresses, banks, and byte values pass and return as integers, so `$70` travels as `112`. Format them as hex on the agent side where that reads better.

- **Errors are tool errors.** A debugger `ERR`, an unknown `session_id`, a timeout, or a refused command comes back as an MCP tool error carrying the underlying message, not a silent failure. The protocol version is checked when the session is created, so a mismatched emulator fails at `create_session`.

- **`x16db` is the raw passthrough.** It forwards one raw debugger line and returns `{"data": [...], "events": [...], "ended": ...}`. The typed tools are the primary interface, since they are discoverable and return parsed values; reach for `x16db` only for a command no tool wraps. It refuses `quit`, `qit`, and `bail`, which would kill the emulator out from under the session, unless `force` is passed, in which case it closes the session and drops it from the registry.

## Index

| Tool | Category | Purpose |
| --- | --- | --- |
| [`create_session`](tools/lifecycle.md#create_session) | [Lifecycle](tools/lifecycle.md) | Boot an emulator and return a session_id |
| [`close_session`](tools/lifecycle.md#close_session) | [Lifecycle](tools/lifecycle.md) | Close a session and stop its emulator |
| [`boot_program`](tools/lifecycle.md#boot_program) | [Lifecycle](tools/lifecycle.md) | Respawn the session on a different program |
| [`protocol_version`](tools/lifecycle.md#protocol_version) | [Lifecycle](tools/lifecycle.md) | The protocol version reported at startup |
| [`continue`](tools/execution.md#continue) | [Execution](tools/execution.md) | Resume the CPU |
| [`break`](tools/execution.md#break) | [Execution](tools/execution.md) | Force the CPU into STOP and report the break |
| [`step`](tools/execution.md#step) | [Execution](tools/execution.md) | Single-step one instruction |
| [`step_over`](tools/execution.md#step_over) | [Execution](tools/execution.md) | Step over a call |
| [`reset`](tools/execution.md#reset) | [Execution](tools/execution.md) | Reset the CPU |
| [`run_until`](tools/execution.md#run_until) | [Execution](tools/execution.md) | Resume and return the next stopping event |
| [`set_breakpoint`](tools/breakpoints.md#set_breakpoint) | [Breakpoints](tools/breakpoints.md) | Arm a breakpoint, optionally conditional |
| [`clear_breakpoint`](tools/breakpoints.md#clear_breakpoint) | [Breakpoints](tools/breakpoints.md) | Clear one breakpoint by location |
| [`clear_all_breakpoints`](tools/breakpoints.md#clear_all_breakpoints) | [Breakpoints](tools/breakpoints.md) | Clear every breakpoint |
| [`enable_breakpoint`](tools/breakpoints.md#enable_breakpoint) | [Breakpoints](tools/breakpoints.md) | Re-enable a disabled breakpoint |
| [`disable_breakpoint`](tools/breakpoints.md#disable_breakpoint) | [Breakpoints](tools/breakpoints.md) | Mute a breakpoint without removing it |
| [`list_breakpoints`](tools/breakpoints.md#list_breakpoints) | [Breakpoints](tools/breakpoints.md) | List the armed breakpoints |
| [`set_watchpoint`](tools/watchpoints.md#set_watchpoint) | [Watchpoints](tools/watchpoints.md) | Arm a read/write watchpoint, optionally conditional |
| [`clear_watchpoint`](tools/watchpoints.md#clear_watchpoint) | [Watchpoints](tools/watchpoints.md) | Clear one watchpoint by id, or all |
| [`enable_watchpoint`](tools/watchpoints.md#enable_watchpoint) | [Watchpoints](tools/watchpoints.md) | Re-enable a disabled watchpoint |
| [`disable_watchpoint`](tools/watchpoints.md#disable_watchpoint) | [Watchpoints](tools/watchpoints.md) | Mute a watchpoint without removing it |
| [`list_watchpoints`](tools/watchpoints.md#list_watchpoints) | [Watchpoints](tools/watchpoints.md) | List the armed watchpoints |
| [`read_registers`](tools/registers.md#read_registers) | [Registers](tools/registers.md) | Read the CPU register snapshot |
| [`set_register`](tools/registers.md#set_register) | [Registers](tools/registers.md) | Set one CPU register by name |
| [`read_memory`](tools/memory.md#read_memory) | [Memory](tools/memory.md) | Read a block of CPU RAM |
| [`write_memory`](tools/memory.md#write_memory) | [Memory](tools/memory.md) | Write bytes to RAM, bypassing I/O |
| [`fill`](tools/memory.md#fill) | [Memory](tools/memory.md) | Fill a range through the CPU write path |
| [`find`](tools/memory.md#find) | [Memory](tools/memory.md) | Search RAM for a byte pattern |
| [`read_vram`](tools/vram.md#read_vram) | [VRAM](tools/vram.md) | Read a block of VRAM |
| [`write_vram`](tools/vram.md#write_vram) | [VRAM](tools/vram.md) | Write bytes to VRAM |
| [`disassemble`](tools/disassembly.md#disassemble) | [Disassembly](tools/disassembly.md) | Disassemble instructions |
| [`clocks`](tools/inspection.md#clocks) | [Inspection](tools/inspection.md) | Cycles since the last resume |
| [`stack`](tools/inspection.md#stack) | [Inspection](tools/inspection.md) | Read the top of the 6502 stack |
| [`zero_page_registers`](tools/inspection.md#zero_page_registers) | [Inspection](tools/inspection.md) | Read the cc65 R0..R15 pseudo-registers |
| [`vera_state`](tools/inspection.md#vera_state) | [Inspection](tools/inspection.md) | Read a VERA state snapshot |
| [`mode`](tools/session.md#mode) | [Session](tools/session.md) | The current machine mode |
| [`state`](tools/session.md#state) | [Session](tools/session.md) | The full state snapshot rows |
| [`set_headers`](tools/session.md#set_headers) | [Session](tools/session.md) | Show or suppress all header lines |
| [`set_header_line`](tools/session.md#set_header_line) | [Session](tools/session.md) | Show or suppress one header line |
| [`screenshot`](tools/capture.md#screenshot) | [Capture](tools/capture.md) | Capture the screen as a PNG image |
| [`x16db`](tools/passthrough.md#x16db) | [Passthrough](tools/passthrough.md) | Forward one raw debugger line |

## Worked example: a corruption hunt

This walks the headline loop: a routine writes `$aa` to zero-page `$70`, and the goal is to catch the instruction that did it. The routine here is injected through `x16db`, but in a real session the program under test arrives via `boot_program` or a `create_session` default.

Boot a session:

```json
create_session()  ->  {"session_id": "7f3a..."}
```

Halt the machine and lay down `LDA #$aa ; STA $70` at `$0500`, then point the program counter at it. These are raw pokes, so they go through `x16db`:

```json
x16db("7f3a...", "brk")
x16db("7f3a...", "wmm 00 0500 a9 aa 85 70")
x16db("7f3a...", "srg pc 0500")
```

Arm a write watchpoint on the byte and run until it is hit:

```json
set_watchpoint("7f3a...", "w", 0, 112)   ->  {"slot": 0}
run_until("7f3a...")
  ->  {"event": "watchpoint", "id": 0, "access": "w",
       "bank": 0, "addr": 112, "val": 170, "pc_bank": 0, "pc": 1282}
```

The hit names the culprit directly: address `112` (`$70`) took the value `170` (`$aa`) from the instruction at `pc` `1282` (`$0502`), the `STA $70`. From the stop, read the surrounding state to understand the context:

```json
read_registers("7f3a...")          ->  {"mode": "c02", "pc": 1282, "a": 170, ...}
read_memory("7f3a...", 0, 112, 1)  ->  {"start": 112, "hex": "aa", "length": 1}
screenshot("7f3a...")              ->  <PNG image block>
```

`continue` again runs on to the next write to `$70`; `list_watchpoints` shows the running hit count; `clear_watchpoint` with the slot removes the watchpoint when the hunt is done.

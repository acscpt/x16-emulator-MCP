# Python API

`x16dbg` is a pure-Python library that drives the Commander X16 emulator's headless debugger over its `-debugstdio` line protocol. It spawns the emulator as a subprocess, sends debugger commands, parses the replies and the asynchronous events that arrive while the CPU runs, and returns typed results. It has no third-party dependencies.

This page is the index to the library reference, with the methods grouped by category under [`api/`](api/). To install the library and run a first session, start with [Getting started](getting-started.md).

## Conventions

- **Numbers are integers, hex on the wire.** Addresses, banks, and byte values are passed as Python `int`; `0x70` and `112` are the same argument. The library formats them as the bare hex the protocol expects. Inside a condition expression the protocol uses C syntax instead, so hex there needs a `$` or `0x` prefix (see [`setWatchpoint`](api/watchpoints.md#setwatchpoint)).

- **Reads return typed results, not strings or dicts.** `readRegisters` returns a `Registers`, `readMemory` returns a `MemoryDump`, `veraState` returns a `VeraState`. Each is a frozen dataclass; see [Result types](api/result-types.md). Commands that return a collection return a `tuple`, never a list.

- **Failures raise, never an error flag.** A debugger `ERR` reply, a broken pipe, or an unparseable line raises `X16dbgError`. A protocol-version mismatch at startup raises `X16ProtocolError`. A resume that never produces its event raises `TimeoutError`. See [Errors](api/errors.md).

- **One emulator per `Client`.** The protocol is request/response with interleaved events, so a single `Client` serializes its commands and is not safe to call from several threads at once. Run separate `Client` instances for parallel work.

---

## Index

| Method | Category | Purpose |
| --- | --- | --- |
| [`Client.launch`](api/lifecycle.md#clientlaunch) | [Lifecycle](api/lifecycle.md) | Spawn the emulator and return a connected client |
| [`close`](api/lifecycle.md#close) | [Lifecycle](api/lifecycle.md) | Tear the subprocess down |
| [`protocolVersion`](api/lifecycle.md#protocolversion) | [Lifecycle](api/lifecycle.md) | The protocol version reported at startup |
| [`transport.command`](api/lifecycle.md#raw-passthrough) | [Lifecycle](api/lifecycle.md) | Send one raw debugger line (escape hatch) |
| [`cont`](api/execution.md#cont) | [Execution](api/execution.md) | Resume the CPU |
| [`brk`](api/execution.md#brk) | [Execution](api/execution.md) | Force the CPU into STOP |
| [`step`](api/execution.md#step) | [Execution](api/execution.md) | Single-step one instruction |
| [`stepOver`](api/execution.md#stepover) | [Execution](api/execution.md) | Step over a call |
| [`reset`](api/execution.md#reset) | [Execution](api/execution.md) | Reset the CPU |
| [`runUntil`](api/execution.md#rununtil) | [Execution](api/execution.md) | Resume and return the next stopping event |
| [`setBreakpoint`](api/breakpoints.md#setbreakpoint) | [Breakpoints](api/breakpoints.md) | Arm a breakpoint, optionally conditional |
| [`clearBreakpoint`](api/breakpoints.md#clearbreakpoint) | [Breakpoints](api/breakpoints.md) | Clear one breakpoint by location |
| [`clearAllBreakpoints`](api/breakpoints.md#clearallbreakpoints) | [Breakpoints](api/breakpoints.md) | Clear every breakpoint |
| [`enableBreakpoint`](api/breakpoints.md#enablebreakpoint) | [Breakpoints](api/breakpoints.md) | Re-enable a disabled breakpoint |
| [`disableBreakpoint`](api/breakpoints.md#disablebreakpoint) | [Breakpoints](api/breakpoints.md) | Mute a breakpoint without removing it |
| [`listBreakpoints`](api/breakpoints.md#listbreakpoints) | [Breakpoints](api/breakpoints.md) | List the armed breakpoints |
| [`setWatchpoint`](api/watchpoints.md#setwatchpoint) | [Watchpoints](api/watchpoints.md) | Arm a read/write watchpoint, optionally conditional |
| [`clearWatchpoint`](api/watchpoints.md#clearwatchpoint) | [Watchpoints](api/watchpoints.md) | Clear one watchpoint by id, or all |
| [`enableWatchpoint`](api/watchpoints.md#enablewatchpoint) | [Watchpoints](api/watchpoints.md) | Re-enable a disabled watchpoint |
| [`disableWatchpoint`](api/watchpoints.md#disablewatchpoint) | [Watchpoints](api/watchpoints.md) | Mute a watchpoint without removing it |
| [`listWatchpoints`](api/watchpoints.md#listwatchpoints) | [Watchpoints](api/watchpoints.md) | List the armed watchpoints |
| [`readRegisters`](api/registers.md#readregisters) | [Registers](api/registers.md) | Read the CPU register snapshot |
| [`setRegister`](api/registers.md#setregister) | [Registers](api/registers.md) | Set one CPU register by name |
| [`readMemory`](api/memory.md#readmemory) | [Memory](api/memory.md) | Read a block of CPU RAM |
| [`writeMemory`](api/memory.md#writememory) | [Memory](api/memory.md) | Write bytes to RAM, bypassing I/O |
| [`fill`](api/memory.md#fill) | [Memory](api/memory.md) | Fill a range through the CPU write path |
| [`find`](api/memory.md#find) | [Memory](api/memory.md) | Search RAM for a byte pattern |
| [`readVram`](api/vram.md#readvram) | [VRAM](api/vram.md) | Read a block of VRAM |
| [`writeVram`](api/vram.md#writevram) | [VRAM](api/vram.md) | Write bytes to VRAM |
| [`disassemble`](api/disassembly.md#disassemble) | [Disassembly](api/disassembly.md) | Disassemble instructions |
| [`clocks`](api/inspection.md#clocks) | [Inspection](api/inspection.md) | Cycles since the last resume |
| [`stack`](api/inspection.md#stack) | [Inspection](api/inspection.md) | Read the top of the 6502 stack |
| [`zeroPageRegisters`](api/inspection.md#zeropageregisters) | [Inspection](api/inspection.md) | Read the cc65 R0..R15 pseudo-registers |
| [`veraState`](api/inspection.md#verastate) | [Inspection](api/inspection.md) | Read a VERA state snapshot |
| [`screenshot`](api/capture.md#screenshot) | [Capture](api/capture.md) | Capture the screen as PNG bytes |
| [`mode`](api/session.md#mode) | [Session](api/session.md) | The current machine mode |
| [`state`](api/session.md#state) | [Session](api/session.md) | The full state snapshot rows |
| [`setHeaders`](api/session.md#setheaders) | [Session](api/session.md) | Show or suppress all header lines |
| [`setHeaderLine`](api/session.md#setheaderline) | [Session](api/session.md) | Show or suppress one header line |

## Reference

- [Result types](api/result-types.md): the frozen dataclasses the reads return, and the `AccessType` / `BreakReason` enums.
- [Errors](api/errors.md): the exception types and when each is raised.
- [Getting started](getting-started.md): installation and a first corruption-hunt session.

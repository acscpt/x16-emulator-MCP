# SPDX-FileCopyrightText: 2026 Heisenberg (acscpt)
# SPDX-License-Identifier: MIT

"""The MCP server: a thin FastMCP layer over the x16dbg client harness.

Each tool is a small adapter that resolves a session, calls one client method,
and returns structured content. No protocol logic lives here; that all belongs
to x16dbg. The tools are snake_case (the agent-facing names) over the client's
camelCase methods.

A session is one emulator subprocess held in the process-local registry. MCP
stdio is a single client per server, so concurrent sessions exist only to let a
client drive several emulators in parallel; each is addressed by its id.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict
from typing import Literal

from mcp.server.fastmcp import FastMCP, Image

from x16dbg.client import Client
from x16dbg.config import discoverEmulator, discoverFsroot, discoverPrg, discoverRom
from x16dbg.models import BreakEvent, WatchHit, Watchpoint

mcp: FastMCP = FastMCP("x16mcp")

# One emulator client per session id. Process-local; not shared across servers.
_sessions: dict[str, Client] = {}


def _getClient(session_id: str) -> Client:
    """Resolve a session id to its client.

    Args:
        session_id: the id returned by create_session.

    Returns:
        Client: the connected client for that session.

    Raises:
        KeyError: when no session has that id.
    """

    client = _sessions.get(session_id)

    if client is None:
        raise KeyError(f"no such session: {session_id}")

    return client


def _launchClient(
    prg: str | None,
    load_addr: int | None,
    run: bool,
    startup_bp: int | None,
) -> Client:
    """Discover the runtime inputs and spawn a connected client.

    Args:
        prg: a PRG to boot, or None to use a configured default if one exists.
        load_addr: an override load address for the PRG.
        run: when True, autostart the loaded program.
        startup_bp: a hex address to break at on startup.

    Returns:
        Client: the connected client, gated on the protocol version.

    Raises:
        FileNotFoundError: when the emulator binary or ROM cannot be found.
        X16ProtocolError: when the emulator reports an unsupported version.
    """

    # Resolve the binary and ROM up front so a missing input fails at session
    # start with a clear message, not later mid-run.
    emulator = discoverEmulator()

    if emulator is None:
        raise FileNotFoundError("x16emu not found; set X16EMU_PATH or drop it in resources/")

    rom = discoverRom()

    if rom is None:
        raise FileNotFoundError("rom.bin not found; set X16ROM_PATH or drop it in resources/")

    # With no explicit PRG, fall back to a configured default if one is present.
    resolved_prg = prg if prg is not None else discoverPrg()

    # The host filesystem root is a server-level setting (X16FS_ROOT), so every
    # session inherits it without the tools carrying a per-call parameter.
    fsroot = discoverFsroot()

    client = Client.launch(
        emulator,
        rom,
        prg=resolved_prg,
        load_addr=load_addr,
        run=run,
        startup_bp=startup_bp,
        fsroot=fsroot,
    )
    return client


def _eventToDict(event: WatchHit | BreakEvent | None) -> dict[str, object]:
    """Shape a stopping event into a JSON-friendly envelope.

    Args:
        event: a watchpoint hit, a break, or None when nothing stopped.

    Returns:
        dict[str, object]: a tagged event with its fields, or {"event": None}.
    """

    # Tag each event so the agent can tell a watchpoint hit from a break, and
    # flatten the enum fields to their string values for JSON.
    if event is None:
        result: dict[str, object] = {"event": None}

    elif isinstance(event, WatchHit):
        result = {
            "event": "watchpoint",
            "id": event.id,
            "access": event.access.value,
            "bank": event.bank,
            "addr": event.addr,
            "val": event.val,
            "pc_bank": event.pc_bank,
            "pc": event.pc,
        }

    else:
        result = {
            "event": "break",
            "reason": event.reason.value,
            "bank": event.bank,
            "addr": event.addr,
        }

    return result


def _watchpointToDict(watchpoint: Watchpoint) -> dict[str, object]:
    """Shape a watchpoint into a JSON-friendly dict.

    Args:
        watchpoint: an armed watchpoint from listWatchpoints.

    Returns:
        dict[str, object]: the watchpoint fields, with access as a plain string.
    """

    # asdict keeps the access enum; flatten it to its wire string for JSON.
    data = asdict(watchpoint)
    data["access"] = watchpoint.access.value
    return data


@mcp.tool()
def create_session(
    prg: str | None = None,
    load_addr: int | None = None,
    run: bool = True,
    startup_bp: int | None = None,
) -> dict[str, str]:
    """Boot an X16 emulator and return a session to drive it.

    The returned session_id is required by every other tool. With no prg, a
    configured default program is booted if one exists, otherwise the machine
    boots to BASIC. The protocol version is gated at startup, so a mismatched
    emulator fails here rather than misbehaving later.

    When the server is configured with a filesystem root (the X16FS_ROOT
    environment variable), the booted machine serves that host directory to
    device 8, so a program's LOAD reads files from it. This is a server-level
    setting shared by every session, not a per-call argument.

    Args:
        prg: a PRG to boot, or None to use a configured default if present.
        load_addr: an override load address for the PRG.
        run: when True, autostart the loaded program.
        startup_bp: a hex address to break at on startup.

    Returns:
        dict[str, str]: the new session_id.
    """

    # Spawn the emulator, then register it under a fresh opaque id.
    client = _launchClient(prg, load_addr, run, startup_bp)
    session_id = str(uuid.uuid4())
    _sessions[session_id] = client

    result = {"session_id": session_id}
    return result


@mcp.tool()
def close_session(session_id: str) -> dict[str, bool]:
    """Close a session and stop its emulator subprocess.

    Args:
        session_id: the session to close.

    Returns:
        dict[str, bool]: an acknowledgment, {"ok": True}, once the session is gone.
    """

    client = _getClient(session_id)
    client.close()
    del _sessions[session_id]

    result = {"ok": True}
    return result


@mcp.tool()
def boot_program(
    session_id: str,
    path: str,
    load_addr: int | None = None,
    run: bool = True,
) -> dict[str, bool]:
    """Load a different program into a session by respawning its emulator.

    The protocol is one subprocess per session, so switching the program under
    test means a fresh spawn; the session keeps its id. The emulator loads a PRG
    by typing LOAD at the BASIC prompt, so the program is present only after the
    machine has run long enough to process it: resume and let it boot, or break
    at the program's entry, rather than reading it immediately. For an in-session
    CPU reset that keeps the same program, use reset. The respawn inherits the
    server's filesystem root (X16FS_ROOT), same as create_session.

    Args:
        session_id: the session to respawn.
        path: the PRG to load.
        load_addr: an override load address for the PRG.
        run: when True, autostart the loaded program.

    Returns:
        dict[str, bool]: an acknowledgment, {"ok": True}, once respawned.
    """

    # Respawn the subprocess on the new program, keeping the session id stable.
    old = _getClient(session_id)
    old.close()

    client = _launchClient(path, load_addr, run, None)
    _sessions[session_id] = client

    result = {"ok": True}
    return result


@mcp.tool()
def protocol_version(session_id: str) -> dict[str, int | None]:
    """Report the debugger protocol version the session reported at startup.

    Args:
        session_id: the session to query.

    Returns:
        dict[str, int | None]: {"protocol_version": <n>}, or None when the
        version check was skipped.
    """

    client = _getClient(session_id)
    result = {"protocol_version": client.protocolVersion}
    return result


@mcp.tool()
def mode(session_id: str) -> dict[str, str]:
    """Report the current machine mode.

    Args:
        session_id: the session to query.

    Returns:
        dict[str, str]: {"mode": <m>} where m is "stop", "run", or "step".
    """

    client = _getClient(session_id)
    result = {"mode": client.mode()}
    return result


@mcp.tool()
def read_registers(session_id: str) -> dict[str, object]:
    """Read the CPU register snapshot.

    Args:
        session_id: the session to read.

    Returns:
        dict[str, object]: the register fields (mode, pc, a, x, y, sp, and so on).
    """

    client = _getClient(session_id)
    registers = client.readRegisters()
    result = asdict(registers)
    return result


@mcp.tool()
def read_memory(session_id: str, bank: int, addr: int, count: int) -> dict[str, object]:
    """Read a contiguous block of CPU RAM.

    Args:
        session_id: the session to read.
        bank: the CPU bank.
        addr: the 16-bit start address.
        count: the number of bytes to read (capped at 0x1000).

    Returns:
        dict[str, object]: the start address, the bytes as a hex string, and the
        byte length.
    """

    client = _getClient(session_id)
    dump = client.readMemory(bank, addr, count)
    result = {"start": dump.start, "hex": dump.data.hex(), "length": len(dump.data)}
    return result


@mcp.tool()
def set_watchpoint(
    session_id: str,
    access: str,
    bank: int,
    addr: int,
    end: int | None = None,
    condition: str | None = None,
) -> dict[str, int]:
    """Arm a read/write watchpoint and return its slot id.

    Args:
        session_id: the session to arm.
        access: "r", "w", or "rw" for reads, writes, or both.
        bank: the bank of the watched location.
        addr: the watched address, or the start of a range.
        end: the inclusive end of a range, or None for a single byte.
        condition: an if-clause expression, or None for an unconditional stop.

    Returns:
        dict[str, int]: {"slot": <id>}, the assigned watchpoint slot.
    """

    client = _getClient(session_id)
    slot = client.setWatchpoint(access, bank, addr, end=end, condition=condition)
    result = {"slot": slot}
    return result


@mcp.tool()
def run_until(session_id: str, timeout: float | None = None) -> dict[str, object]:
    """Resume the CPU and return the next stopping event.

    The headline corruption-hunt step: with a watchpoint armed, this runs until
    the watched location is accessed and reports the instruction that did it.

    Args:
        session_id: the session to resume.
        timeout: seconds to wait for the stop, or None for the default.

    Returns:
        dict[str, object]: a tagged watchpoint or break event with its fields, or
        {"event": None} when nothing stopped within the timeout.
    """

    client = _getClient(session_id)
    event = client.runUntil(timeout=timeout)
    result = _eventToDict(event)
    return result


@mcp.tool()
def x16db(session_id: str, command: str, force: bool = False) -> dict[str, object]:
    """Forward one raw line to the debugger and return its response.

    It passes a command straight through for cases the typed tools do not cover,
    such as a rarely-used command or an experiment; the typed tools are the
    primary interface and return parsed values, while this returns the raw
    response lines. The session-ending commands (quit, qit, bail) are refused
    unless force is set, since they kill the emulator out from under the session;
    with force the session is closed and dropped from the registry so it stays
    consistent. The "ended" field reports whether the call ended the session.

    Args:
        session_id: the session to drive.
        command: the raw debugger command line.
        force: when True, allow the session-ending commands (quit, qit, bail).

    Returns:
        dict[str, object]: {"data", "events", "ended"} -- the response data and
        event lines, and whether the command ended the session.

    Raises:
        ValueError: when command would end the session and force is False.
    """

    client = _getClient(session_id)

    stripped = command.strip()
    head = stripped.split(maxsplit=1)[0] if stripped else ""
    ending = head in {"quit", "qit", "bail"}

    if ending and not force:
        raise ValueError(f"{head!r} would end the session; use close_session, or pass force=true")

    # A forced session-ender terminates the emulator, so send it, reap the
    # process, and drop the session to keep the registry consistent.
    if ending:
        try:
            client.transport.send(command)

        except OSError:
            pass

        client.close()
        del _sessions[session_id]

        result: dict[str, object] = {"data": [], "events": [], "ended": True}
        return result

    response = client.transport.command(command)
    result = {"data": response.data, "events": response.events, "ended": False}
    return result


@mcp.tool(name="continue")
def cont(session_id: str) -> dict[str, bool]:
    """Resume the CPU from STOP.

    Args:
        session_id: the session to resume.

    Returns:
        dict[str, bool]: an acknowledgment, {"ok": True}.
    """

    client = _getClient(session_id)
    client.cont()
    result = {"ok": True}
    return result


@mcp.tool(name="break")
def brk(session_id: str) -> dict[str, object]:
    """Force the CPU into STOP and report the resulting break.

    Args:
        session_id: the session to halt.

    Returns:
        dict[str, object]: the tagged break event.
    """

    client = _getClient(session_id)
    event = client.brk()
    result = _eventToDict(event)
    return result


@mcp.tool()
def step(session_id: str) -> dict[str, object]:
    """Single-step one instruction and report the break.

    Args:
        session_id: the session to step.

    Returns:
        dict[str, object]: the tagged step break event.
    """

    client = _getClient(session_id)
    event = client.step()
    result = _eventToDict(event)
    return result


@mcp.tool()
def step_over(session_id: str, timeout: float | None = None) -> dict[str, object]:
    """Step over a call, reporting the break when the step completes.

    Args:
        session_id: the session to step.
        timeout: seconds to wait for the completing event, or None for the default.

    Returns:
        dict[str, object]: the tagged step break event.
    """

    client = _getClient(session_id)
    event = client.stepOver(timeout=timeout)
    result = _eventToDict(event)
    return result


@mcp.tool()
def reset(session_id: str) -> dict[str, bool]:
    """Reset the CPU, leaving the rest of the machine state intact.

    Args:
        session_id: the session to reset.

    Returns:
        dict[str, bool]: an acknowledgment, {"ok": True}.
    """

    client = _getClient(session_id)
    client.reset()
    result = {"ok": True}
    return result


@mcp.tool()
def set_breakpoint(
    session_id: str,
    bank: int,
    addr: int,
    condition: str | None = None,
) -> dict[str, bool]:
    """Arm a breakpoint at a bank and address, optionally conditional.

    Args:
        session_id: the session to arm.
        bank: the X16 RAM/ROM bank (used only for $A000-$FFFF; 0 otherwise).
        addr: the address to stop at.
        condition: an if-clause expression, or None for an unconditional stop.

    Returns:
        dict[str, bool]: an acknowledgment, {"ok": True}.
    """

    client = _getClient(session_id)
    client.setBreakpoint(bank, addr, condition=condition)
    result = {"ok": True}
    return result


@mcp.tool()
def clear_breakpoint(session_id: str, bank: int, addr: int) -> dict[str, bool]:
    """Clear the breakpoint at a bank and address.

    Args:
        session_id: the session to clear from.
        bank: the bank of the breakpoint.
        addr: the address of the breakpoint.

    Returns:
        dict[str, bool]: an acknowledgment, {"ok": True}.
    """

    client = _getClient(session_id)
    client.clearBreakpoint(bank, addr)
    result = {"ok": True}
    return result


@mcp.tool()
def clear_all_breakpoints(session_id: str) -> dict[str, bool]:
    """Clear every breakpoint.

    Args:
        session_id: the session to clear.

    Returns:
        dict[str, bool]: an acknowledgment, {"ok": True}.
    """

    client = _getClient(session_id)
    client.clearAllBreakpoints()
    result = {"ok": True}
    return result


@mcp.tool()
def enable_breakpoint(session_id: str, bank: int, addr: int) -> dict[str, bool]:
    """Re-enable a disabled breakpoint.

    Args:
        session_id: the session holding the breakpoint.
        bank: the bank of the breakpoint.
        addr: the address of the breakpoint.

    Returns:
        dict[str, bool]: an acknowledgment, {"ok": True}.
    """

    client = _getClient(session_id)
    client.enableBreakpoint(bank, addr)
    result = {"ok": True}
    return result


@mcp.tool()
def disable_breakpoint(session_id: str, bank: int, addr: int) -> dict[str, bool]:
    """Mute a breakpoint without removing it.

    Args:
        session_id: the session holding the breakpoint.
        bank: the bank of the breakpoint.
        addr: the address of the breakpoint.

    Returns:
        dict[str, bool]: an acknowledgment, {"ok": True}.
    """

    client = _getClient(session_id)
    client.disableBreakpoint(bank, addr)
    result = {"ok": True}
    return result


@mcp.tool()
def list_breakpoints(session_id: str) -> dict[str, list[dict[str, object]]]:
    """List the armed breakpoints.

    Args:
        session_id: the session to list.

    Returns:
        dict[str, object]: {"breakpoints": [...]}, one dict per breakpoint.
    """

    client = _getClient(session_id)
    breakpoints = [asdict(breakpoint_) for breakpoint_ in client.listBreakpoints()]
    result = {"breakpoints": breakpoints}
    return result


@mcp.tool()
def clear_watchpoint(session_id: str, which: int | Literal["*"]) -> dict[str, bool]:
    """Clear one watchpoint by slot id, or all of them with "*".

    Args:
        session_id: the session to clear from.
        which: the slot id, or "*" for every watchpoint.

    Returns:
        dict[str, bool]: an acknowledgment, {"ok": True}.
    """

    client = _getClient(session_id)
    client.clearWatchpoint(which)
    result = {"ok": True}
    return result


@mcp.tool()
def enable_watchpoint(session_id: str, slot_id: int) -> dict[str, bool]:
    """Re-enable a disabled watchpoint.

    Args:
        session_id: the session holding the watchpoint.
        slot_id: the slot id of the watchpoint.

    Returns:
        dict[str, bool]: an acknowledgment, {"ok": True}.
    """

    client = _getClient(session_id)
    client.enableWatchpoint(slot_id)
    result = {"ok": True}
    return result


@mcp.tool()
def disable_watchpoint(session_id: str, slot_id: int) -> dict[str, bool]:
    """Mute a watchpoint without removing it.

    Args:
        session_id: the session holding the watchpoint.
        slot_id: the slot id of the watchpoint.

    Returns:
        dict[str, bool]: an acknowledgment, {"ok": True}.
    """

    client = _getClient(session_id)
    client.disableWatchpoint(slot_id)
    result = {"ok": True}
    return result


@mcp.tool()
def list_watchpoints(session_id: str) -> dict[str, list[dict[str, object]]]:
    """List the armed watchpoints.

    Args:
        session_id: the session to list.

    Returns:
        dict[str, object]: {"watchpoints": [...]}, one dict per watchpoint.
    """

    client = _getClient(session_id)
    watchpoints = [_watchpointToDict(watchpoint) for watchpoint in client.listWatchpoints()]
    result = {"watchpoints": watchpoints}
    return result


@mcp.tool()
def set_register(session_id: str, name: str, value: int) -> dict[str, bool]:
    """Set one CPU register by name.

    Args:
        session_id: the session to modify.
        name: the register name (pc, a, b, c, x, y, sp, p, k, db, dp, e).
        value: the new value.

    Returns:
        dict[str, bool]: an acknowledgment, {"ok": True}.
    """

    client = _getClient(session_id)
    client.setRegister(name, value)
    result = {"ok": True}
    return result


@mcp.tool()
def write_memory(session_id: str, bank: int, addr: int, values: list[int]) -> dict[str, bool]:
    """Write bytes to CPU RAM, bypassing I/O side effects.

    Args:
        session_id: the session to write to.
        bank: the CPU bank.
        addr: the 16-bit start address.
        values: the byte values to write in order.

    Returns:
        dict[str, bool]: an acknowledgment, {"ok": True}.
    """

    client = _getClient(session_id)
    client.writeMemory(bank, addr, values)
    result = {"ok": True}
    return result


@mcp.tool()
def fill(session_id: str, bank: int, addr: int, value: int, count: int = 1) -> dict[str, bool]:
    """Fill a range of CPU RAM with a byte through the CPU write path.

    Args:
        session_id: the session to write to.
        bank: the CPU bank.
        addr: the 16-bit start address.
        value: the byte written at each position.
        count: the number of bytes to write.

    Returns:
        dict[str, bool]: an acknowledgment, {"ok": True}.
    """

    client = _getClient(session_id)
    client.fill(bank, addr, value, count)
    result = {"ok": True}
    return result


@mcp.tool()
def find(
    session_id: str,
    bank: int,
    start: int,
    length: int,
    pattern: list[int],
) -> dict[str, list[int]]:
    """Search a range of CPU RAM for a byte pattern.

    Args:
        session_id: the session to search.
        bank: the CPU bank.
        start: the 16-bit start of the search range.
        length: the length of the range in bytes.
        pattern: the byte pattern to find (1 to 16 bytes).

    Returns:
        dict[str, object]: {"matches": [...]}, the start address of each match.
    """

    client = _getClient(session_id)
    matches = list(client.find(bank, start, length, pattern))
    result = {"matches": matches}
    return result


@mcp.tool()
def read_vram(session_id: str, addr: int, count: int) -> dict[str, object]:
    """Read a contiguous block of VRAM.

    Args:
        session_id: the session to read.
        addr: the 17-bit VRAM start address.
        count: the number of bytes to read (capped at 0x1000).

    Returns:
        dict[str, object]: the start address, the bytes as a hex string, and the
        byte length.
    """

    client = _getClient(session_id)
    dump = client.readVram(addr, count)
    result = {"start": dump.start, "hex": dump.data.hex(), "length": len(dump.data)}
    return result


@mcp.tool()
def write_vram(session_id: str, addr: int, values: list[int]) -> dict[str, bool]:
    """Write bytes to VRAM, straight to the VRAM buffer.

    Args:
        session_id: the session to write to.
        addr: the 17-bit VRAM start address.
        values: the byte values to write in order.

    Returns:
        dict[str, bool]: an acknowledgment, {"ok": True}.
    """

    client = _getClient(session_id)
    client.writeVram(addr, values)
    result = {"ok": True}
    return result


@mcp.tool()
def disassemble(session_id: str, bank: int, addr: int, count: int) -> dict[str, list[str]]:
    """Disassemble instructions starting at an address.

    Args:
        session_id: the session to disassemble.
        bank: the CPU bank.
        addr: the 16-bit start address.
        count: the number of instructions (capped at 0x40).

    Returns:
        dict[str, object]: {"lines": [...]}, one verbatim disassembly line each.
    """

    client = _getClient(session_id)
    lines = list(client.disassemble(bank, addr, count))
    result = {"lines": lines}
    return result


@mcp.tool()
def clocks(session_id: str) -> dict[str, int]:
    """Report the CPU cycles elapsed since the last resume.

    Args:
        session_id: the session to query.

    Returns:
        dict[str, int]: {"clocks": <n>}.
    """

    client = _getClient(session_id)
    result = {"clocks": client.clocks()}
    return result


@mcp.tool()
def stack(session_id: str, count: int = 16) -> dict[str, list[dict[str, int]]]:
    """Read the top of the 6502 stack.

    Args:
        session_id: the session to read.
        count: the number of bytes to read (capped at 0x40).

    Returns:
        dict[str, object]: {"stack": [...]}, each entry an address and value.
    """

    client = _getClient(session_id)
    entries = [asdict(entry) for entry in client.stack(count)]
    result = {"stack": entries}
    return result


@mcp.tool()
def zero_page_registers(session_id: str) -> dict[str, list[int]]:
    """Read the cc65 zero-page R0..R15 pseudo-registers.

    Args:
        session_id: the session to read.

    Returns:
        dict[str, object]: {"registers": [...]}, sixteen words indexed R0..R15.
    """

    client = _getClient(session_id)
    registers = list(client.zeroPageRegisters())
    result = {"registers": registers}
    return result


@mcp.tool()
def vera_state(session_id: str) -> dict[str, object]:
    """Read a snapshot of VERA's internal state.

    Args:
        session_id: the session to read.

    Returns:
        dict[str, object]: the VERA register fields.
    """

    client = _getClient(session_id)
    state = client.veraState()
    result = asdict(state)
    return result


@mcp.tool()
def state(session_id: str) -> dict[str, list[str]]:
    """Read the full debugger state snapshot as labeled rows.

    Args:
        session_id: the session to read.

    Returns:
        dict[str, object]: {"state": [...]}, the snapshot rows verbatim.
    """

    client = _getClient(session_id)
    rows = list(client.state())
    result = {"state": rows}
    return result


@mcp.tool()
def set_headers(session_id: str, on: bool) -> dict[str, bool]:
    """Show or suppress all per-prompt header lines.

    Args:
        session_id: the session to configure.
        on: True to show the header lines, False to suppress them.

    Returns:
        dict[str, bool]: an acknowledgment, {"ok": True}.
    """

    client = _getClient(session_id)
    client.setHeaders(on)
    result = {"ok": True}
    return result


@mcp.tool()
def set_header_line(session_id: str, line: str | int, on: bool) -> dict[str, bool]:
    """Show or suppress one header line.

    Args:
        session_id: the session to configure.
        line: the header line, by name (cpu, aux, view, bp) or number (1-4).
        on: True to show the line, False to suppress it.

    Returns:
        dict[str, bool]: an acknowledgment, {"ok": True}.
    """

    client = _getClient(session_id)
    client.setHeaderLine(line, on)
    result = {"ok": True}
    return result


@mcp.tool()
def screenshot(session_id: str) -> Image:
    """Capture the current screen as a PNG image.

    Args:
        session_id: the session to capture.

    Returns:
        Image: the screen as a PNG image block.
    """

    client = _getClient(session_id)
    png = client.screenshot()
    image = Image(data=png, format="png")
    return image


def _closeAllSessions() -> None:
    """Close every live session so server shutdown leaks no emulator process."""

    # Best effort per client: one that fails to close must not strand the rest.
    for client in _sessions.values():
        try:
            client.close()

        except Exception:
            pass

    _sessions.clear()


def main() -> None:
    """Run the MCP server over stdio, the console entry point."""

    # FastMCP owns the JSON-RPC / stdio framing and its own event loop; close any
    # sessions left open when it returns so no emulator is orphaned.
    try:
        mcp.run(transport="stdio")

    finally:
        _closeAllSessions()


if __name__ == "__main__":
    main()

# Changelog

All notable changes to x16-emulator-mcp. The format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

This project is alpha. The set of tools, their return formats, and their defaults may change without warning until v1.0.

## [Unreleased]

## [0.1.1] - 2026-06-08

### Fixed

- **The debugger prompt is now treated as a record separator, not a trailing terminator.** An asynchronous event (a breakpoint or watchpoint firing) arrives with its own prompt and no `RDY`, so a single read could hold several prompts. The transport now retains anything past the first prompt for the next read, and a command drains any pending event ahead of its own reply. This fixes `read_registers` and `mode` intermittently failing with a leaked `x16db > ` prompt in their output, and makes `run_until` reliably report a stopping event instead of occasionally dropping it.

- **`clear_watchpoint` rejects a malformed string id.** A string that is not exactly `*` (a quoted `"*"`, a stray slot number) was passed straight through to the debugger and returned an error. The wrapper now validates it, and the tool's schema accepts only an int or `"*"`.

## [0.1.0] - 2026-06-06

### Added

- **`x16mcp`** - an MCP server harness exposing 40 tools including session management, memory inspection, conditional breakpoints and watchpoints, and other tools. See `docs/tool-reference.md`.

- **`x16dbg`** - a Python (standard-library) harness for the X16 Emulator `-debugstdio` debugger. See `docs/python-api.md`.

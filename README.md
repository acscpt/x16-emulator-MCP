# x16-emulator-MCP

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Tests](https://github.com/acscpt/x16-emulator-MCP/actions/workflows/tests.yml/badge.svg)](https://github.com/acscpt/x16-emulator-MCP/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/acscpt/x16-emulator-MCP/branch/develop/graph/badge.svg)](https://codecov.io/gh/acscpt/x16-emulator-MCP)

x16-emulator-MCP is a Python [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that lets an AI application boot, drive, and interrogate a real [Commander X16](https://github.com/X16Community) emulator through its headless `-debugstdio` debugger. The agent works the way a person would at a debugger: set breakpoints and memory watchpoints, run, read registers, memory, and VRAM, evaluate conditions, and look at the screen.

Ask an AI agent something like:

> A routine is clobbering zero-page `$70` and I don't know which one. Put a write watchpoint on it, run, and tell me what writes there.

A moment later the answer comes back in the tool-result pane: `$0070 written as $aa by the instruction at $0502`. Catching the program counter behind a stray write is the loop the project is built for.

x16-emulator-MCP drives a [fork of the Commander X16 emulator](https://github.com/acscpt/x16-emulator) that carries the headless debugger protocol it speaks. Install and configure the emulator before using the server; the [installation guide](docs/installation.md) walks through it.

## What the AI agent can do with it

The server exposes the debugger as a set of typed tools; the [tool reference](docs/tool-reference.md) documents each with a worked example.

- Boot a headless X16 session against a ROM, optionally loading a PRG at the BASIC prompt, and keep several independent sessions open at once, each addressed by a session id.

- Set execution breakpoints and read or write memory watchpoints, including conditional ones, then run to the next hit. Each watchpoint hit names the program counter behind the access, which is what makes corruption hunting work.

- Read and write CPU registers, system memory, and VRAM, and disassemble instructions.

- Inspect the call stack, the zero-page registers, and the machine's banking and status state.

- Capture the screen as a PNG.

- Reach the raw debugger directly through a passthrough tool when no typed tool covers a command, and tear every session down cleanly on disconnect.

## Use it as a Python library

 **`x16dbg`** is a pure-standard-library package for use in regular Python modules, scripts and  can run unattended in a test suite or a CI pipeline and is the foundation of the `x16mcp` MCP server.

 Programmatically arm a watchpoint, run a routine, and assert on where it stopped:

```python
from x16dbg import Client, discoverEmulator, discoverRom

def testStoreHitsZeroPage():
    with Client.launch(discoverEmulator(), discoverRom()) as x16:
        x16.brk()                                                # halt the running machine
        x16.writeMemory(0x00, 0x0500, [0xA9, 0xAA, 0x85, 0x70])  # LDA #$aa ; STA $70
        x16.setRegister("pc", 0x0500)

        x16.setWatchpoint("w", 0x00, 0x70)                       # stop on any write to $70
        hit = x16.runUntil()

        assert hit.pc == 0x0502
```

The [Python API](docs/python-api.md) documents every method, and [getting started](docs/getting-started.md) walks a first session end to end.

## Licence

MIT. See [LICENSE](LICENSE).

## Acknowledgements

Thanks to the [Commander X16](https://github.com/X16Community) community and the authors of [X16Community/x16-emulator](https://github.com/X16Community/x16-emulator).

## Fork Notice

**x16-emulator-MCP** depends on a [fork of x16-emulator](https://github.com/acscpt/x16-emulator) that implements a headless `-debugstdio` debugger protocol.

The emulator and ROM are not distrubted as part of this repository or its release artefacts. The ROM is licensed separately and you need to install both seperately. See the [Installation Guide](docs/installation.md#install-the-emulator) for more details.

## Disclaimer

x16-emulator-MCP is a separate project from the Commander X16 emulator and is not affiliated with, sponsored, or endorsed by the [X16Community](https://github.com/X16Community) project.

For the canonical emulator source and documentation, see [X16Community/x16-emulator](https://github.com/X16Community/x16-emulator).

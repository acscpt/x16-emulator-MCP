# x16-emulator-MCP

A Python client harness and MCP server for the Commander X16 emulator's headless stdio debugger (`-debugstdio`). It lets an AI agent debug X16 software the way a human would at a debugger: set breakpoints and memory watchpoints, run, inspect registers, memory, and VRAM, evaluate conditions, and look at the screen. The headline use case is memory-corruption hunting: arm a write watchpoint on a clobbered address, run, and each hit names the program counter that wrote it.

The project is built in two layers:

- `x16dbg`, a pure-standard-library client harness that drives the debugger protocol. It has no third-party dependencies and is usable on its own from a REPL or a script.

- `x16mcp`, a thin MCP server that wraps the harness and exposes each capability as a tool. It depends only on the MCP SDK, installed through the `server` extra.

The emulator is the platform this rides on; it is not bundled. See the development notes for how the binary and ROM are discovered.

## Status

Early development. The harness is being built first, then the MCP server on top.

## Development

```sh
pip install -e ".[dev,server]"   # harness + server + test tooling
pip install -e ".[dev]"          # harness only, no MCP dependency
pytest                            # runs the suite with coverage and writes tests/TEST_REPORT.md
ruff check . && ruff format --check .
```

Tests run against the live emulator under the SDL dummy video driver and skip cleanly when the binary or ROM is absent. Provide them by setting `X16EMU_PATH` and `X16ROM_PATH`, or by dropping `x16emu` and `rom.bin` into a local `resources/` folder at the repo root. The ROM is separately licensed and is not part of this repository.

## License

MIT.  See [LICENSE](LICENSE)

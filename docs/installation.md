# Installation guide

x16-emulator-MCP runs as an MCP server that an MCP client (Claude Desktop, Claude Code, the Gemini CLI, Cursor, and so on) can communicate with.

A Python library is also provided for those who want to drive the emulator directly from a Python API, the way a test suite or a CI pipeline would.

Both use cases share the same driver and the same emulator subprocess underneath. Once installed and wired up, the client (or the library) can call tools like `create_session`, `set_watchpoint`, and `run_until` to drive a live X16 session.

The steps to get there are:

1. Install the Commander X16 emulator binary and a ROM.
2. Install x16-emulator-MCP itself.
3. Configure your MCP client to spawn the server.

## Prerequisites

- Python 3.10 or newer.

- An MCP client. [Claude Desktop](https://claude.ai/download), [Claude Code](https://claude.com/claude-code), the [Gemini CLI](https://github.com/google-gemini/gemini-cli), and [Cursor](https://cursor.sh) are common choices. Any client that speaks the [Model Context Protocol](https://modelcontextprotocol.io) over stdio will work.

- A Commander X16 emulator binary and a `rom.bin`, covered in the next section.

- `git`, a C toolchain, and the SDL2 development libraries, needed only for the build-from-source option below.

## Install the emulator

x16-emulator-MCP drives the emulator over its headless `-debugstdio` line protocol, and it requires the [acscpt/x16-emulator](https://github.com/acscpt/x16-emulator) fork, which carries the protocol (currently `proto=2`) and the primitives the server depends on:

1. The headless `-debugstdio` debugger REPL itself: a line protocol the driver speaks to set breakpoints and watchpoints, run, and read state without a window or audio.

2. A `scr` command that screenshots the current frame to a PNG file. The server reads that file and returns the bytes through the [`screenshot`](tools/capture.md) tool.

3. Breakpoint enable/disable and replace-on-readd semantics, used by the breakpoint tools.

4. A fix so breakpoints fire in the banked `$A000-$FFFF` window, not only in low RAM.

5. VERA's frame timing ticks under `-debugstdio`, so a program paced off the VBL flag (`$9F27` bit 0) runs to completion instead of spinning forever.

6. The memory commands honour an explicit bank for the `$A000-$BFFF` window, so `read_memory` and `write_memory` address a named HiRAM bank directly regardless of which bank the CPU has selected.

The minimum fork version that ships all of these is the [`r50-next-acscpt.4`](https://github.com/acscpt/x16-emulator/releases) release.

There are two ways to obtain the binary.

### Download a release binary

Tagged releases are published at [github.com/acscpt/x16-emulator/releases](https://github.com/acscpt/x16-emulator/releases). Download the headless build for your platform and mark it executable.

The emulator also needs a `rom.bin` at runtime, and the ROM is not part of the emulator download. Get it from the [X16Community/x16-rom releases](https://github.com/X16Community/x16-rom/releases); the `rom.bin` from a matching release pairs with the emulator version.

### Build from source

Building the fork needs a C toolchain and the SDL2 development libraries.

```bash
# Clone the fork and check out the integration branch
git clone https://github.com/acscpt/x16-emulator.git
cd x16-emulator
git checkout develop

# Build; the binary lands at build/x16emu
make
```

A `rom.bin` is still needed separately, from the [X16Community/x16-rom releases](https://github.com/X16Community/x16-rom/releases).

### Point the server at them

The server finds the binary and the ROM from, in order: an explicit path passed in code, the `X16EMU_PATH` and `X16ROM_PATH` environment variables, or a `resources/` folder at the repository root holding `x16emu` and `rom.bin`. The MCP client config below sets the two environment variables; the `resources/` folder is the convenient route for the Python library and the test suite.

## Install x16-emulator-MCP

For a standard install, use PyPI. The server needs the MCP SDK, which the `server` extra pulls in:

```bash
# Create and activate a venv
python -m venv ~/.venvs/x16-emulator-mcp
source ~/.venvs/x16-emulator-mcp/bin/activate   # Windows: ...\Scripts\activate

# Install with the server extra
pip install "x16-emulator-mcp[server]"
```

For a development install:

```bash
# Clone the repo
git clone https://github.com/acscpt/x16-emulator-MCP.git
cd x16-emulator-MCP

# Create and activate a venv
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install in editable mode with dev and server extras
pip install -e ".[dev,server]"
```

Both paths install the `x16mcp` command-line entry point inside the venv. Installing without the `server` extra (`pip install x16-emulator-mcp`) gives you the `x16dbg` library alone, with no third-party dependency, for the Python-library use below.

## Wire up an MCP client

MCP clients learn about servers from a JSON config file. The format is the same across most clients (an `mcpServers` object keyed by server name); only the file location differs.

A typical entry:

```json
{
  "mcpServers": {
    "x16": {
      "command": "/absolute/path/to/x16-emulator-MCP/.venv/bin/x16mcp",
      "args": [],
      "env": {
        "X16EMU_PATH": "/absolute/path/to/x16emu",
        "X16ROM_PATH": "/absolute/path/to/rom.bin"
      }
    }
  }
}
```

Three paths must be absolute:

- `command` is the path to the `x16mcp` entry point inside the venv where you installed the server.

- `X16EMU_PATH` and `X16ROM_PATH` point at the emulator binary and the ROM. The MCP client spawns the server in an unspecified working directory, so relative paths will not resolve.

### Claude Code

Register the server with the `claude mcp add` command, choosing the scope you want (`local`, `project`, or `user`):

```bash
claude mcp add --scope user x16 \
  -e X16EMU_PATH=/absolute/path/to/x16emu \
  -e X16ROM_PATH=/absolute/path/to/rom.bin \
  -- /absolute/path/to/.venv/bin/x16mcp
```

Run `claude mcp add --help` for the full set of options. Project scope writes an `.mcp.json` at the project root.

### Claude Desktop

Edit `claude_desktop_config.json` and add the entry above under `mcpServers`:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Restart Claude Desktop after editing.

### Gemini CLI

The [Gemini CLI](https://github.com/google-gemini/gemini-cli) reads the same `mcpServers` shape from its settings file, at `~/.gemini/settings.json` for all projects or `.gemini/settings.json` for one project:

```json
{
  "mcpServers": {
    "x16": {
      "command": "/absolute/path/to/.venv/bin/x16mcp",
      "env": {
        "X16EMU_PATH": "/absolute/path/to/x16emu",
        "X16ROM_PATH": "/absolute/path/to/rom.bin"
      }
    }
  }
}
```

Newer versions also accept `gemini mcp add`; see the [Gemini CLI MCP docs](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/configuration.md) for the current options.

### Other MCP clients

The table below links to setup docs for other common MCP clients. The entry is the standard one above; the quirks column notes where a client departs from it.

| Client | Config location | Schema quirk | Docs |
| --- | --- | --- | --- |
| Cursor | `~/.cursor/mcp.json` or `.cursor/mcp.json` | adds explicit `"type": "stdio"` | [cursor.com](https://cursor.com/docs/context/mcp) |
| VS Code | `.vscode/mcp.json` | top-level key is `servers`, not `mcpServers` | [code.visualstudio.com](https://code.visualstudio.com/docs/copilot/chat/mcp-servers) |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | none, matches the standard entry | [docs.windsurf.com](https://docs.windsurf.com/windsurf/cascade/mcp) |
| Zed | `~/.zed/settings.json` (and OS variants) | top-level key is `context_servers`; `command` is a nested object | [zed.dev](https://zed.dev/docs/ai/mcp) |
| Cline (VS Code) | Cline MCP UI panel | `mcpServers` plus `disabled` and `autoApprove` fields | [docs.cline.bot](https://docs.cline.bot/mcp/configuring-mcp-servers) |
| Continue.dev | `.continue/mcpServers/*.yaml` | YAML, one server per file | [docs.continue.dev](https://docs.continue.dev/customize/deep-dives/mcp) |

Any other MCP client that speaks stdio JSON-RPC accepts the same idea with its own location. Consult the client's documentation.

## Use as a Python library

The driver the server wraps is importable on its own as `x16dbg`, with no MCP dependency. It is the route for driving the emulator from a script, a test suite, or a CI pipeline, where the determinism of a real debugger session is the point: arm a watchpoint, run a known routine, and assert on where it stopped.

See the [Python API](python-api.md) for a per-method reference and [getting started](getting-started.md) for an end-to-end walk-through. Dropping `x16emu` and `rom.bin` into a `resources/` folder at the repository root lets `discoverEmulator()` and `discoverRom()` find them with no configuration, which keeps a test suite portable.

## Verify

With the venv activated, start the server manually to confirm the install:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0.1"}}}' | x16mcp
```

A JSON-RPC response containing `"serverInfo":{"name":"x16mcp", ...}` confirms the server is running.

The handshake does not exercise the emulator binary. The first `create_session` call from your MCP client confirms `X16EMU_PATH` and `X16ROM_PATH` resolve correctly. For an end-to-end walk-through, see [getting started](getting-started.md).

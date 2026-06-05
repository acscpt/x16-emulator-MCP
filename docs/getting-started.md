# Getting started

Install `x16dbg`, point it at an emulator binary and a ROM, and run a first debugging session. For the full method reference, see the [Python API](python-api.md).

## Installation

The library needs Python 3.10 or later and installs from the project package with no extras:

```bash
pip install -e .
```

At runtime it spawns the emulator, so an `x16emu` binary and a `rom.bin` must be present. Discovery looks in three places, in order: an explicit path passed in code, the `X16EMU_PATH` / `X16ROM_PATH` environment variables, and a local `resources/` folder at the repository root. `discoverEmulator()` and `discoverRom()` return the resolved `Path`, or `None` when nothing is found. The emulator binary is built from the `acscpt/x16-emulator` fork; the ROM is licensed separately and is not bundled.

## Quickstart

The headline use case is finding what corrupts a memory location. Arm a write watchpoint on the byte, run, and each hit names the program counter that wrote it. This session installs a two-instruction routine that stores `$aa` into zero-page `$70`, then catches the store:

```python
from x16dbg import Client, discoverEmulator, discoverRom

with Client.launch(discoverEmulator(), discoverRom()) as x16:
    x16.brk()                                                 # halt the running machine
    x16.writeMemory(0x00, 0x0500, [0xA9, 0xAA, 0x85, 0x70])   # LDA #$aa ; STA $70
    x16.setRegister("pc", 0x0500)

    x16.setWatchpoint("w", 0x00, 0x70)                        # stop on any write to $70
    hit = x16.runUntil()

    print(f"${hit.addr:04x} took ${hit.val:02x} from the store at ${hit.pc:04x}")
    # $0070 took $aa from the store at $0502
```

`Client.launch` spawns the emulator, runs the startup handshake, and checks the protocol version before returning. The `with` block closes the subprocess on exit. `runUntil` resumes the CPU and returns the next stopping event, here a `WatchHit` carrying the watched address, the byte written, and the writing program counter.

From here, the [Python API](python-api.md) covers every method, the [result types](api/result-types.md) the reads return, and the [errors](api/errors.md) they raise.

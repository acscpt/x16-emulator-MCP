# Session

The debugger is a window onto the emulator's internal machine state, and it keeps a session of its own around that view. The commands here report on that session: the machine's current mode, a one-shot snapshot of everything the debugger is tracking, and control over which header lines the emulator prints before each prompt. They are the housekeeping around the rest of the API, useful for orienting a script that has just attached or quieting the per-prompt output when a clean stream matters.

---

## `mode`

```python
mode() -> str
```

The current machine mode: `"stop"`, `"run"`, or `"step"`.

[^ Index](../python-api.md#index)

---

## `state`

```python
state() -> tuple[str, ...]
```

The full debugger state snapshot as labeled rows: the mode, the view cursor, the CPU program counter, the clock, and any breakpoints (with their X16 bank). The rows are returned verbatim, since the snapshot is formatted for reading rather than parsing.

[^ Index](../python-api.md#index)

---

## `setHeaders`

```python
setHeaders(on) -> None
```

Show or suppress all per-prompt header lines. The transport already separates header lines from command data, so suppressing them is a convenience, not a requirement for clean parsing.

[^ Index](../python-api.md#index)

---

## `setHeaderLine`

```python
setHeaderLine(line, on) -> None
```

Show or suppress one header line, named (`cpu`, `aux`, `view`, `bp`) or numbered (`1`-`4`).

[^ Index](../python-api.md#index)

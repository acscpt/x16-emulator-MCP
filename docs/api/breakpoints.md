# Breakpoints

A breakpoint stops the CPU when execution reaches an address. Breakpoints are keyed by location, not by a slot id, so there is at most one per location and clearing names the location. Below `$A000` the location is just the address. In the `$A000-$FFFF` window the breakpoint is bank-specific: its full identity is the address plus the X16 RAM/ROM bank, and it fires only while that bank is the one mapped there. The window's bank changes at runtime (the KERNAL runs in RAM bank 1), so a banked breakpoint is implicitly scoped to the bank it was set in.

---

## `setBreakpoint`

```python
setBreakpoint(bank, addr, *, condition=None) -> None
```

Arm a breakpoint. Re-arming a location already set replaces it in place: the condition is updated, or cleared when none is given. The table holds 16 breakpoints, and a further one raises.

**Parameters**

- `bank` *(int)*: the X16 RAM/ROM bank, used only for addresses in the `$A000-$FFFF` window; pass `0x00` for unbanked low memory.

- `addr` *(int)*: the address to stop at.

- `condition` *(str or None)*: a condition expression for the `if` clause, passed verbatim. The condition is C-style: decimal by default, hex with a `$` or `0x` prefix. It reads live state at the hit, such as `a == $ff` or `mem[$30] == $01`.

**Example**

```python
x16.setBreakpoint(0x00, 0xC04F, condition="a == $ff")
```

[^ Index](../python-api.md#index)

---

## `clearBreakpoint`

```python
clearBreakpoint(bank, addr) -> None
```

Clear the breakpoint at a location.

**Errors**

- `X16dbgError` when no breakpoint is set there.

[^ Index](../python-api.md#index)

---

## `clearAllBreakpoints`

```python
clearAllBreakpoints() -> None
```

Clear every breakpoint.

[^ Index](../python-api.md#index)

---

## `enableBreakpoint`

```python
enableBreakpoint(bank, addr) -> None
```

Re-enable a disabled breakpoint so it stops the CPU again.

**Errors**

- `X16dbgError` when no breakpoint is set there.

[^ Index](../python-api.md#index)

---

## `disableBreakpoint`

```python
disableBreakpoint(bank, addr) -> None
```

Mute a breakpoint without removing it. It keeps its condition and shows as disabled in [`listBreakpoints`](#listbreakpoints).

**Errors**

- `X16dbgError` when no breakpoint is set there.

[^ Index](../python-api.md#index)

---

## `listBreakpoints`

```python
listBreakpoints() -> tuple[Breakpoint, ...]
```

List the armed breakpoints, in the order they were added. Empty when none are set. See [`Breakpoint`](result-types.md#breakpoint) for the fields; note that the listing reports the program bank, not the X16 bank a banked breakpoint was armed with (which appears in [`state`](session.md#state)).

[^ Index](../python-api.md#index)

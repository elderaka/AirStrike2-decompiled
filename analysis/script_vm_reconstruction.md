# Script VM reconstruction — second static pass

The project has been copied to `E:\Decomp\AirStrike2`. The uploaded installer and extracted executable hashes match the first-pass samples. Original programs remain unexecuted. The project now includes a corpus-wide script decoder, recovered engine bindings, and a runnable semantic reconstruction of radar rotation.

## Established structure

The container loader begins at preferred-base VA **0x00429d40**. It reads a **56-byte header** and checks the literal `RCSL`. All 631 supplied script containers have version field **16**. Every container passed chunk bounds, counted-name, function/definition count, DATA size, string-size, code-size, and entry-point-range checks.

| Header offset | Recovered meaning |
|---|---|
| 0x00 | RCSL magic |
| 0x04 | Version field, 16 in all samples |
| 0x08 | Cached resource count |
| 0x0c | External definition count |
| 0x10 | External function count |
| 0x14 | DATA initializer count |
| 0x18 | Runtime slot count |
| 0x1c | STRG byte count |
| 0x20 | CODE instruction count |
| 0x24–0x34 | Five entry-point instruction indices; -1 means absent |

The default/update entry is the index at **0x28**. The exact names of the other four event entries remain provisional; dispatch values 1–4 select the other header fields through the scheduler. Slots contain four-byte values, including float values and address-like values.

Chunks have four-character tags followed by a little-endian payload size. Observed loader tags include `DEFS`, `FUNC`, `DATA`, `STRG`, `CODE`, and `CASH` (spelled this way in the binary). DEFS and FUNC use byte-length-prefixed, null-terminated names. DATA uses eight-byte initializer records (`int16 type`, `int16 slot`, `uint32 value`). Initialization code at **0x00429c30** handles type 2 as a float value and type 3 as an address into the slot array. CASH contents remain outside the implemented decoder's semantic model; the original files and chunk sizes are preserved.

Each instruction is **14 bytes**: opcode byte, flags byte, and three signed 32-bit operand fields at offsets 2, 6, and 10. The interpreter starts at **0x004268f0**; its 31-entry dispatch table is at **0x00426e90**. An instruction budget of 10,000 is visible in the interpreter; stack limit checks use 512 entries.

Operand flags identify immediate float A (bit 0), dereference A (bit 1), immediate float B (bit 4), dereference B (bit 5), and dereference C (bit 7). Nonnegative references normally address the runtime slot array. Negative references can resolve external definitions; branch/function/allocation opcodes use some operand fields as raw indices instead. The decoder preserves raw operands rather than pretending all operands share one type.

## Dispatch map

These names describe handlers recovered from native disassembly. The decoder lists them but does not execute them. Integer conversion behavior, unusual floating-point values, and all pointer semantics still need executable-level equivalence checks before a full VM implementation.

| Opcode | Role |
|---:|---|
| 0 | Yield/end the current interpreter invocation |
| 1–4 | Multiply, divide, add, subtract |
| 5–6 | Integer-converted bitwise AND, OR |
| 7–8 | Integer-converted logical OR, AND |
| 9–10 | Integer-converted equality, inequality |
| 11–14 | Greater than, less than, greater/equal, less/equal for ordinary finite inputs |
| 15–16 | Integer-converted logical NOT, float negation |
| 17 | MOVE: A receives B |
| 18 | Indexed address computation: result is base plus four times index |
| 19–20 | PUSH and POP |
| 21 | Allocate memory |
| 22–23 | Default/advance handler; unused in supplied corpus |
| 24 | Return value/end invocation |
| 25–27 | Jump if zero, jump if nonzero, relative unconditional jump |
| 28 | Call function; negative index resolves external binding |
| 29 | Call with wait/resume behavior |
| 30 | Set wait duration/state |

The script update dispatcher at **0x00426f10** restores the default entry when the interpreter stops on opcode 0 or 24. This establishes that the radar's end instruction does not permanently disable its default update routine. Relative jumps bypass the normal one-instruction increment when taken; exact NaN truth behavior is not represented by the ordinary branch labels.

## Engine bindings recovered

`analysis/vm_bindings.json` records **101 function names and native addresses**, **28 definition names and two selector addresses each**, and all 31 handler addresses. The external function table begins at **0x00461f38**, and the definition table at **0x00462270**. The two definition addresses are selected by runtime context; player-specific ownership is not fully modeled yet.

Examples of directly recovered function bindings:

| Function | VA |
|---|---|
| rotatez | 0x00427f40 |
| sleep | 0x00427f60 |
| Shoot | 0x00427f70 |
| Damage | 0x00428410 |
| RadialDamage | 0x00428490 |
| TerrainHeight | 0x00428b30 |
| StartSound | 0x00428cc0 |
| EndLevel | 0x0040e290 |

The corpus contains 51,617 instructions. MOVE occurs 13,118 times, indexed-address computation 12,062 times, CALL 6,905 times, and CALL_WAIT 1,366 times. `Shoot` is bound in 146 script files, `Damage` in 117, and `rotatez` in 140. These are script-binding counts, not counts of actual gameplay executions.

## First reconstructed behavior: radar rotation

The 131-byte `assets/pak1/scripts/radar.scr` decodes to:

```text
entry 0
slot[0] = 60.0
call external rotatez(slot[0])
end invocation
```

The native `rotatez` handler reads the first parameter and global frame time, then adds their product to a field at offset **0x40 in the current script context**. The arithmetic is:

```text
angle_z = angle_z + rate * frame_seconds
```

The meaning of the angle unit, handedness, and visible rotation direction remains unverified. The routine does not wrap the angle on this observed path. The enclosing game driver caps the frame step at 100 ms; `rotatez` itself uses the already supplied step.

`reconstruction/radar.py` provides readable functions for this behavior. Its checks inspect the actual binary script fixture, verify the expected opcode sequence and constant, and exercise elapsed-time rotation, zero frame step, and a negative rotation rate. Ten 100 ms steps accumulate approximately 60 angle units. The code models float storage rounding but does not claim exact x87 extended-precision behavior for every input.

Both focused checks passed:

- Radar fixture and arithmetic checks.
- Invalid/truncated chunk, opcode, function-index and instruction-count rejection; all 631 corpus containers and their five entry-point fields.

This is a real, small reconstruction grounded in script bytes and the native function implementation. It is not yet a replacement VM, an independently observed visual result, or a playable game.

## Next milestone

Implement enough of the VM and object context to run one projectile script: typed slot/address resolution, arithmetic, calls, relative branches, return/yield, and wait state. Pair it with one player weapon/object definition. Trace `Shoot` and `Damage` bindings rather than inventing firing or collision behavior. Validate the reconstructed interpreter on the radar and another short script before expanding to the full corpus.

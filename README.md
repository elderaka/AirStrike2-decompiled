# AirStrike2 reconstruction project

This is a static reverse-engineering project for the Air Assault 2 distribution whose internal game executable is AirStrike2.exe. The original installer, game, and DLLs have not been executed.

## Project contents

- `original/`: unchanged uploaded installer.
- `game/`: installer payload extracted without installation; includes executable, BASS, configuration, and original APK archives.
- `assets/`: all 2,359 recovered archive files, kept separated by archive, with SHA-256 manifests.
- `analysis/`: initial PE map, imports, resources, disassembly, cross-references, script listings, and binding tables.
- `tools/`: archive reader, script decoder, binding mapper, and focused checks. `packages/` contains the locally installed PE/disassembly libraries.
- `reconstruction/`: readable reconstructed behavior with runnable checks.

## Current result

The APK archive reader is reconstructed. All **631 RCSL script containers** (630 SCR files and one SC file) decode into **51,617 instructions**. The executable exposes **101 external function bindings**, **28 variable bindings**, and **31 opcode dispatch entries**.

The first reconstructed gameplay-adjacent behavior is the radar rotation script and its native `rotatez` routine. This is semantic reconstruction; there is no playable replacement game yet. See `analysis/script_vm_reconstruction.md` for evidence, addresses, and limitations.

## Run the current checks

From this project directory, with Python 3.9 or newer:

```powershell
python tools/check_script_decoder.py
python reconstruction/radar.py
```

These run only the newly written Python tools. They do not launch the original game.

To regenerate script listings and engine binding tables:

```powershell
python tools/decode_scripts.py
python tools/map_vm_bindings.py
```

To extract an original archive into a new folder:

```powershell
python tools/reconstruct_apk.py game/data/pak1.apk work/reextracted_pak1
```

The initial game map is `analysis/reverse_engineering_map.md`. The next substantial milestone is a script interpreter with entity, wait/callback, and collision bindings sufficient to reconstruct one weapon end to end. Runtime comparison should occur only if necessary, in an isolated VM.

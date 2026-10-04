# Air Assault 2 — initial static reverse-engineering map

Analysis date: 4 October 2026. Neither the uploaded installer nor any extracted executable or DLL was executed or loaded. The only executable used for extraction was the separately downloaded innoextract utility; the game remained input data throughout.

## Main result

`Air_Assault2.exe` is an Inno Setup 5.2.1 installer. Its payload contains the actual game, `AirStrike2.exe`, a separate `game.exe` launcher, `XbrowserLite.exe`, BASS audio middleware, configuration, logos, and three custom asset archives. The game window title is **AirAssault II - Divo Games**; the configuration identifies version **v 2.45**, copyright **2003–2007 DivoGames**. This explains the different uploaded and internal filenames.

The game code is directly disassemblable. The first recovered subsystem is its asset archive reader: a working Python reconstruction extracts **2,359 files**, including mission configuration, weapon/object definitions, textures, models, audio, and compiled scripts.

## Identity and provenance

| File | Bytes | SHA-256 |
|---|---:|---|
| Uploaded installer | 23,071,855 | `e779b8623dc1aea7bef79b2235ce27aa4f26a4a4aff6568aa31d01423be0b41e` |
| AirStrike2.exe | 417,792 | `efba05b176776369ac9f9dceb04c62193730a58b12bc1685c1106cef3d0ce58a` |
| game.exe | 57,344 | `70934ce32cef37bf25d7a207110b2760242e634b227c56f9a97a858cba19f16a` |

The uploaded attachment was retrieved from the original conversation's local attachment path. The referenced `/mnt/data` path does not exist on this Windows host.

Extraction used [innoextract 1.9 from its official site](https://constexpr.org/innoextract/), which extracts Inno installers without running their installer code. The downloaded ZIP's MD5 matched the site's published `72d0d0dd874b6236eaa44411f4470ee1`. This is an integrity comparison, not a cryptographic signature verification. Extraction completed with no reported failure; its file list is in `extraction_log.txt`.

## PE architecture and toolchain clues

| Property | Installer | Actual game |
|---|---|---|
| Architecture | PE32, x86 (`0x014c`) | PE32, x86 (`0x014c`) |
| Subsystem | Windows GUI | Windows GUI |
| Preferred image base | `0x00400000` | `0x00400000` |
| Entry-point RVA | `0x00009a54` | `0x00038f0c` |
| Entry-point VA | `0x00409a54` | `0x00438f0c` |
| Linker field | 2.25 | 8.0 |
| Compiler inference | Borland/Delphi-style Inno loader | Native C/C++, strongly consistent with MSVC 8 / Visual Studio 2005-era tools |

The game's Microsoft-style RTTI includes `std::bad_alloc`, `std::length_error`, `IntroPageImage`, `IntroPageDivoGames`, and `Utility::XmlNodeImpl`. A Rich header is present, and the entry point calls a security-cookie initialization candidate before entering CRT startup. Together with linker 8.0, these support the MSVC inference. Exact compiler edition, flags, and original source structure remain unknown. There is no CLR data directory; a stray `mscoree.dll` string belongs to runtime support rather than evidence of a managed game.

The game COFF timestamp decodes to **2007-01-16 13:59:53 UTC**, consistent with the user's release-era context. It is a header value, not independently verified build history. No debug/PDB record, export table, or version resource was found in the game. Runtime settings supply the v 2.45 label.

## Game sections

| Section | RVA | Virtual bytes | Raw bytes | Entropy, bits/byte | Permissions |
|---|---|---:|---:|---:|---|
| .text | `0x1000` | 315,333 | 315,392 | 6.73 | read, execute |
| .rdata | `0x4e000` | 71,606 | 73,728 | 6.05 | read |
| .data | `0x60000` | 30,883,196 | 16,384 | 3.63 | read, write |
| .rsrc | `0x1dd4000` | 4,872 | 8,192 | 3.30 | read |

The very large virtual `.data` section is mostly zero-initialized storage. Numerous accesses to high-address globals fit large static pools/arrays; this alone is not a packing indicator.

The installer has `CODE`, `DATA`, `BSS`, `.idata`, `.tls`, `.rdata`, `.reloc`, and `.rsrc`. Its overlay begins at file offset **53,248**, spanning **23,018,607 bytes**. Explicit Inno/LZMA strings and successful extraction identify installer compression. That compression should not be confused with a protected game executable.

## Imports and likely middleware

Complete function lists and IAT addresses are in each file's `pe_inventory.json`.

| Imported library | Observed functions / implication |
|---|---|
| OPENGL32.dll | Context creation, immediate-mode geometry, vertex arrays, textures, fog, display lists; fixed-function OpenGL renderer |
| GLU32.dll | `gluPerspective`, `gluBuild2DMipmaps` |
| GDI32.dll | Pixel-format setup and `SwapBuffers` |
| BASS.dll | Sample/music loading, playback, channel control, 3D audio; supplied DLL version resource says **2.1**, Un4seen Developments |
| WINMM.dll | `timeGetTime`, timer-resolution setup, joystick enumeration/polling |
| USER32.dll | Window creation, message dispatch, keyboard/mouse messages, fullscreen/display handling |
| KERNEL32.dll | File access, INI settings, allocation, CRT support |
| WININET.dll | HTTP connection/request functions; likely score posting, consistent with Settings.xml, but no network behavior was observed |
| ADVAPI32.dll | Registry writes |
| SHELL32.dll | `ShellExecuteA`; external-link behavior is also configured in Settings.xml |

The evidence points to a **custom DivoGames engine** with OpenGL, BASS, custom asset loaders, and a custom scripting runtime. No Unity/Unreal identifier was found. The exact internal engine name is not established. XML RTTI identifies a custom wrapper/API, not a specific underlying XML library.

`game.exe` contains `AirStrike2.exe` and a GameTop statistics URL, and imports `CreateProcessA`; it is a launcher candidate rather than the gameplay analysis target. `XbrowserLite.exe` is bundled separately. Their presence does not establish which paths run during gameplay.

## Packer/protector assessment and resources

No strong evidence of a whole-executable packer was found in `AirStrike2.exe`: ordinary section names, moderate code entropy, extensive readable imports/strings, normal CRT startup, and readable game code. It has no overlay and no TLS directory. This is an initial static assessment, not proof that all protection checks are absent. `IsDebuggerPresent` is imported, but that can occur in MSVC runtime support and is insufficient to label the game protected.

The game has five resource leaves: one icon image, one group icon, and three dialogs (IDs 120, 121, 141). Locale IDs include Russian 1049 and German 1031. Raw resource contents were extracted. Bulk gameplay assets are external archives, not PE resources. Installer resources additionally include strings, version metadata, a manifest, and loader data.

Settings.xml includes CD-check and score-posting switches both set to zero in this distribution, plus an exit link. These configuration values were inspected, not altered; corresponding runtime enforcement was not traced in full.

## Entry point and main-loop map

Addresses below are preferred-base **VAs in AirStrike2.exe**, not file offsets. Names are analyst labels unless corroborated by a diagnostic string. Linear disassembly supplied the map; a complete recursive control-flow graph has not yet been built.

| VA | Candidate role | Evidence / confidence |
|---|---|---|
| `0x00438f0c` | PE entry | Calls `0x00441ed3`, jumps to `0x00438d2c`; confirmed instructions |
| `0x00441ed3` | Security-cookie setup | Startup pattern; high confidence |
| `0x00438d2c` | CRT startup | Runtime initialization then four-argument call to `0x00405b60` at `0x00438e9e`; high confidence |
| `0x00405b60` | WinMain / game driver | Establishes working directory, parses command line, loads settings, initializes game, loops; high confidence |
| `0x00425e20` | Settings loader | `Settings.xml` reference; high confidence |
| `0x00405950` | Engine initialization | Seeds randomness, opens log, initializes filesystem, window/graphics, sound, timer resolution |
| `0x00405cc0` | Frame-loop back edge | Calls `timeGetTime`, computes elapsed milliseconds, clamps to 100 |
| `0x00415a70` | Windows message pump | PeekMessage/GetMessage/TranslateMessage/DispatchMessage |
| `0x00410b30` | Frame/game dispatcher | Called every loop; multiple update/render calls and entity-list traversal; exact subpass ordering still to label |
| `0x004168b0` | Joystick update | `joyGetPosEx`, button/axis processing |
| `0x0042a570` | Audio update candidate | Called each loop after joystick processing; further tracing needed |
| `0x00419b00` | Render/presentation pass | Called by frame dispatcher; contains `SwapBuffers` at `0x00419c2c` |
| `0x00415b60` | Window procedure | Message switches including key and mouse messages; high confidence |

The loop's time step is `min(unsigned(now - previous), 100) * 0.001` seconds. The `0.001` constant was read from the binary. It accumulates global time values and invokes the message/frame/joystick/audio candidates. This supports a variable-time-step driver with a 100 ms cap; it does not yet establish the simulation's full pause, catch-up, or interpolation behavior.

## First reconstruction: APK asset filesystem

`reconstruct_apk.py` is a standalone standard-library implementation. It reads data only and validates archive bounds and destination paths. It implements the observed archive decoding, not the game's entire virtual-file API.

| Offset | Layout |
|---|---|
| 0 | 32-bit version bits `0x3f800000` (float 1.0) |
| 4 | 32-bit tag `0x00009999` |
| 8 | Little-endian directory offset |
| 12 | Little-endian entry count |
| 16 | 1,024-byte XOR key |
| 1,040 onward | File payloads |
| Directory offset | XOR-encoded records, 76 bytes each |

Each directory record contains a 64-byte null-terminated filename, a 32-bit absolute file offset, a 32-bit size, and a 32-bit payload-XOR flag. The directory is always decoded from key position zero. Nonzero payload flags cause the same XOR transform; payload key position is relative to the file, not the archive. All observed flags are zero or one. No per-entry decompression is used on this observed read path.

The original transform at **`0x00405db0`** is equivalent, for valid nonnegative positions, to:

```cpp
void xor_buffer(unsigned char* data, int length, int position,
                const unsigned char key[1024]) {
    for (int i = 0; i < length; ++i)
        data[i] ^= key[(position + i) % 1024];
}
```

Its original register convention uses ECX for the buffer, ESI for length, EDI for position, and a stack argument for the key. This C++ is semantic pseudocode, not original source or a binary-matching reconstruction. Signed overflow/negative positions are outside the reconstructed valid-input contract.

Supporting functions: **`0x00405df0`** loads an archive, reads a `0x410`-byte header, allocates `count * 0x4c` bytes, seeks to and decodes its directory; **`0x00405f10`** enumerates `data\\*.apk`; **`0x00406100`** resolves files; **`0x004064c0`** reads them and conditionally decodes payloads using the current file position; **`0x00406550`** returns file size. The compiled loader allows up to 128 archive slots.

Run with Python 3.9 or newer:

```text
python reconstruct_apk.py path/to/pak1.apk destination/pak1
```

## Recovered contents and validation

| Archive | Files | Contents |
|---|---:|---|
| pak0.apk | 1,609 | 761 TGA textures, 847 MDL models, one MAX file |
| pak1.apk | 705 | 21 HSC maps, mission list, 39 OBJ definitions, nine PS definitions, four WPN definitions, 630 SCR scripts, one SC file |
| pak2.apk | 45 | Five MO3 music files and 40 WAV sound files |

Fifty-three pak1 payloads require XOR decoding. All directory record names decoded into usable paths. All 2,359 extracted sizes and output hashes were verified against the extraction manifests, and duplicate names within each archive were checked. All 761 TGA files fully decoded through Pillow. All 40 WAV files have RIFF/WAVE headers, all five music files have MO3 headers, and all 630 scripts have RCSL headers. The output ZIP passed its CRC integrity check. These checks provide static format evidence, not playback/gameplay equivalence.

The XOR helper's runnable checks cover round-trip decoding and chunk-relative key position across the 1,024-byte wrap. They do not prove every virtual-filesystem behavior. `asset_validation.json` records the observed checks.

`recovered_assets.zip` preserves archive separation as pak0/pak1/pak2 and includes their complete manifests. Some extensions are custom: OBJ files inspected here are text object definitions, not necessarily Wavefront meshes; APK is not Android packaging; SCR files are compiled script data and must not be launched as Windows screensavers.

Useful concrete data: `pak1/maps/levels.txt` names 18 mission IDs and two intro IDs. `pak1/weapons/player.wpn` defines `p_wpn_machinegun` with `mgun_proj`, `mgun_flash`, and speed 1600. The definition alone does not establish speed units or all firing behavior.

## Next steps, in order

1. **Import AirStrike2.exe into Ghidra as x86 PE**, retain base `0x00400000`, and label the addresses above. Follow calls recursively from WinMain and the frame dispatcher, separating CRT support from game functions. Treat this map's names as provisional until decompiler/control-flow review confirms them.
2. **Recover the script container and VM before recreating gameplay by guesswork.** RCSL scripts contain `DEFS`, `FUNC`, `DATA`, and `CODE` chunks. Loader comparisons are visible at `0x00429e29`, `0x00429e9f`, `0x00429eaa`, `0x00429eb5`, and `0x0042a051`. Resolve the external-function table using strings such as `Shoot`, `Damage`, `sleep`, `rotatez`, and `EndLevel`. Start with the small `scripts/radar.scr` script, which names `rotatez`; decode argument/instruction semantics before claiming a reconstructed behavior.
3. **Trace one weapon end to end.** Start with `p_wpn_machinegun`, locate its projectile and flash object definitions, then follow script loading, the `Shoot` binding, collision/damage, and timing. Weapon parser references occur at `0x00414fbf` and `0x0041511a`; unknown-weapon diagnostics at `0x00415218` help anchor registration/lookup. Build a small data-driven test with measured behavior as acceptance criteria.
4. **Decode map and model formats.** Mission-list loader starts at `0x0040d530`; model-header checks cluster near `0x0041cb97` and `0x0041cbc9`. Use the tutorial HSC and one small MDL as fixtures. Establish coordinate units, vertex layout, terrain height, tags, and animation before building a viewer.
5. **Only if static evidence leaves a concrete gap, run the game in an isolated VM.** Use a snapshot, disable network and host/shared-folder access for the run, and log the exact sample hashes. Capture tutorial input, frame timing, firing rate, movement, and collisions. No such execution was needed or performed for this pass.

## Deliverables and limits

The output folders hold PE inventories, ASCII/UTF-16 string listings with **file offsets**, raw PE resources, entry disassemblies, a game linear disassembly, and import/string cross-references. Address labels in disassembly are **VAs**; do not confuse them with string-file offsets. The evidence bundle also includes inspection and validation scripts plus tool versions.

This establishes a practical starting map and a working asset subsystem. It does not recover the original full source, prove all code paths, establish gameplay equivalence, or produce a playable port. Asset formats, script opcodes, entity layouts, physics, and rendering details remain the next substantive reverse-engineering work.

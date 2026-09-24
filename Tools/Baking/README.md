# Baked resource letter case

## Symptom

Critters render as a 1x1 placeholder (only the name tag is visible) while tiles, walls, scenery,
and the interface draw correctly. `TLA_Client.log` reports nothing.

`--Render.CritterStubSpriteName art/tiles/ADB001.FRM` drawing the critter as that tile confirms the
frames are not found rather than drawn wrongly.

## Root cause

Resource lookup is case-sensitive: `DataSource::CachedDir` and `FileSystem::_pathToIndex` are keyed by
the real on-disk names, and `ResourceManager` builds critter frame names in **lower** case
(`art/critters/hmjmpsaa.frm`). `ImageBaker` deliberately lowercases critter art
(`ImageBaker.cpp`, `collection.NewName = strex(fname).lower()` for `art/critters/`), and the section
key in `Baking/<Pack>/SpriteInfo/<Pack>.foinfo` — the path the renderer asks for — is lower case too.

The baked files nevertheless ended up **upper** case (the spelling inside the source `fo_art*.zip`),
because `MasterBaker` derived the "expected output spelling" from the **input** path instead of the
path the baker actually wrote:

- `Baker.cpp` — `PreparePackContext`'s `bake_checker` recorded the path passed by the baker, which for
  `ImageBaker` is the input file name from the mounted pack.
- `Baker.cpp` — `CollectExpectedOutputs` then filled `ExpectedOutputs::Paths` from those input names.
- `Baker.cpp` — `SweepOutdatedOutputs` renamed every freshly written `hmjmpsaa.frm` back to
  `HMJMPSAA.FRM` to match that assumed spelling.

Measured on this tree: 5138 renames per bake (FOArt 4119, LongHairDude 563, BlackCombatArmor 219,
FOnline 195, Lieutenant 42) — exactly the number of sprite files, all under `art/critters/`.
Writing the lower-cased name onto an existing upper-cased file on NTFS does not change the file name,
so the mismatch survived every bake and every startup prebake.

## Fix

`BakerOutputSpelling.patch` (git format, applies to `Engine/Source/Tools/Baker.cpp`) records the paths
the bakers actually **write** and uses them for the spelling map, while the input paths keep owning the
deletion claim:

- new `PackBakeContext::BakedOutputPaths`, guarded by the existing `BakedFilePathsLocker`;
- `write_data` records the output path it is about to write;
- `CollectExpectedOutputs` builds `ResourceNames` from `BakedFilePaths` (case-folded identity, used to
  decide what is outdated) and `Paths` from `BakedOutputPaths` (exact spelling, used to decide what is
  misspelled).

The patch is currently **applied in the `Engine` submodule working tree**. It is exported here so it can
be upstreamed and so a submodule update does not lose it:

```bash
git -C Engine apply Tools/Baking/BakerOutputSpelling.patch      # re-apply
git -C Engine checkout -- Source/Tools/Baker.cpp                # revert
```

## Verification

```powershell
cmake --build Build --config Release --target ForceBakeResources   # ~2m30s, status success
(Get-ChildItem .\Baking\FOArt\art\critters -Filter '*hmjmpsaa*').Name   # hmjmpsaa.frm
Select-String -Path .\TLA_Baker.log -Pattern 'Rename stale-cased file'  # 0 matches
cmake --build Build --config Release --target BakeResources        # incremental, as startup prebake does
(Get-ChildItem .\Baking\FOArt\art\critters -Filter '*hmjmpsaa*').Name   # still hmjmpsaa.frm
```

`SpriteInfo/FOArt.foinfo` keeps `[art/critters/hmjmpsaa.frm]` with `SourcePath = art/critters/HMJMPSAA.FRM`
— lookup key and disk name now agree, and the input archive spelling is still recorded as provenance.

## Normalize-BakedArtCase.ps1

Repair and audit tool for trees baked by an **unpatched** engine (for example
`Binaries/Server-Windows-win64/Baking`): it reads the section keys from `SpriteInfo/*.foinfo` and
renames the real files to match, two-step through a temporary name so a case-only rename works on
NTFS. Idempotent — a tree baked with the patch reports zero mismatches.

Scripts are blocked by the default execution policy, so invoke it explicitly:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Tools\Baking\Normalize-BakedArtCase.ps1 -DryRun
powershell -NoProfile -ExecutionPolicy Bypass -File .\Tools\Baking\Normalize-BakedArtCase.ps1
```

Run it with the client and server closed. The file is saved as UTF-8 **with BOM** so Windows
PowerShell 5.1 does not read its messages as ANSI.

## Startup prebake

There is no configuration flag for it. `AppInitFlags::PrebakeResources` is hard-coded in
`ClientApp.cpp`, `ClientLib.cpp`, and `ServerHeadlessApp.cpp`, and `ApplicationInit.cpp` runs it for
every unpackaged start. Removing `TLA_BakerLib.dll` next to the executable is the only engine-free way
to disable it: `ApplicationInit.cpp` then only logs a warning while `Baking/` exists (suppressed with
`Baking.IgnoreMissingBakerWarning = True`). With the patch applied this is unnecessary — the prebake
run leaves the case correct.

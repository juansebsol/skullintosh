# Development

## Setup

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
skullintosh doctor
pytest                      # unit tests (no network)
pytest -m network           # end-to-end builds against the real pinned releases
ruff check src tests && ruff format --check src tests
skullintosh scan-secrets
```

The runtime has **no third-party Python dependencies** (stdlib only: `tomllib`, `plistlib`,
`zipfile`, `urllib`). `pytest` and `ruff` are for development.

## Repository layout

```text
manifests/dependencies.toml   pinned releases (repo, tag, asset, sha256) and where kexts live
profiles/
  _common/                    overlays shared by all profiles (+ debug, + fat32 installer)
  monterey/                   profile.toml (kexts, ACPI, drivers, features) + config overlay
  ventura/ sonoma/ sequoia/ tahoe/   research profiles
hardware/
  usb/nuc6i7kyb.toml          USB port map source (generates USBMap.kext)
  reference/nuc6i7kyk.toml    expected device IDs for inventory reconciliation
src/skullintosh/              the CLI (see below)
scripts/inventory/            read-only hardware inventory (Linux, Windows)
scripts/backup/               read-only boot-environment backups (Linux, Windows)
licenses/                     third-party license texts at the pinned tags
tests/                        unit tests + network-marked end-to-end tests
docs/                         user and contributor documentation
build/  dist/  .cache/  local/   generated or private; all git-ignored
```

| Module | Responsibility |
| --- | --- |
| `manifest.py` | Load and validate the manifest (approved owners, hash format) |
| `fetch.py` | Download to `.cache/downloads`, verify SHA-256, `pin` new assets |
| `profiles.py` | Load profiles, feature conditions, CLI overrides |
| `overlay.py` | Schema-checked overlay merge onto OpenCore's `Sample.plist` |
| `usbmap.py` | Codeless USB map kext generation |
| `build.py` | Assemble the EFI in a temp dir, write `provenance.json`, move into place |
| `validate.py` | Static checks and `ocvalidate` |
| `package.py` | Deterministic release zip with licenses and README-FIRST |
| `identity.py` / `secretscan.py` | SMBIOS identity handling and secret scanning |
| `report.py` | Sanitized environment and inventory reports |

## How a build works

1. Resolve the profile, apply `--set` feature overrides, and pick items whose `when` and
   `flavors` match.
2. Verify the cached release zips against the manifest, or download and verify them.
3. Extract OpenCore's `X64/EFI` core files, the selected drivers and tools, and the sample ACPI
   binaries **from one archive**; extract kexts from their archives (zip-slip and symlinks
   rejected).
4. Load that archive's `Docs/Sample.plist`, empty the collections Skullintosh owns (ACPI/Add,
   Kernel/Add, Drivers, Tools, DeviceProperties/Add, NVRAM/Add, …), apply overlays (schema- and
   type-checked), then generate Kernel/Add (with `ExecutablePath` read from each kext's
   Info.plist and per-OS `MinKernel`/`MaxKernel`), ACPI/Add, UEFI/Drivers, Misc/Tools and
   boot-args.
5. Write `config.plist` (sorted keys) and `provenance.json` (no timestamps or absolute paths),
   so identical inputs give identical bytes.

## Changing things

* **A config value:** edit the profile overlay. Put the reason in a `#Key` sibling string and the
  evidence in the pull request. If the key doesn't exist in the pinned OpenCore schema, the build
  fails.
* **A dependency version:** edit `manifests/dependencies.toml`, clear the hash, and run
  `skullintosh pin <package>`. It cross-checks GitHub's published digest when there is one.
  Refresh `licenses/<package>.txt` from the new tag and note the change in CHANGELOG.md. Any
  version change resets that profile's hardware status to "needs re-test".
* **A new kext:** add a `[kexts.X]` entry (with `darwin_min/max` if it's OS-specific), then
  reference it in profiles. New GitHub owners must be added to `approved_owners` in a separate,
  reviewed change.
* **USB map:** see [usb-mapping.md](usb-mapping.md).
* **Profile status:** only move to `verified` with a linked hardware report
  ([hardware-testing.md](hardware-testing.md)). `tests/test_profiles.py` fails if any profile is
  `verified`, so that test must be updated in the same PR with the evidence link.

## Safety rules for code

* Never write to an ESP, call `diskutil`/`bless`/`efibootmgr -c`/`bcdedit /set`, or mount disks.
  `tests/test_repo_files.py` checks the scripts for the most dangerous commands.
* Treat downloaded archives as untrusted: verify the hash before opening, reject unsafe paths.
* Don't log personal data. Reports go through `report.sanitize`.

## Releases

1. Update CHANGELOG.md and the version in `pyproject.toml` / `src/skullintosh/__init__.py`.
2. `skullintosh build --target monterey` (release and debug), `skullintosh package …`.
3. Packages carry the profile status in their name (`-candidate`) unless the profile is
   `verified`.
4. Tag, then attach the zips and `.sha256` files to the GitHub release (automated later: B-096).

# Progress report: 2026-10-28 (v0.1.0 "Foundation", unreleased)

**Summary:** the research, tooling, validation and documentation that need no hardware are in
place. A first, informal hardware session on 2026-10-28/29 installed and booted Monterey 12.7.6
on the reference NUC from the debug flavour (details below). No formal test report exists yet,
so every hardware cell in [compatibility.md](compatibility.md) is still an expectation or an
informal observation, not a verified result.

## First hardware session (2026-10-28/29)

What happened, in order, with the debug flavour (`DBG-108`) on a USB stick made with
`createinstallmedia` (12.7.6, offline installer):

1. The first boot halted in OpenCore with `Grabbed zero system-id for SB`. Fixed in the build
   (`SystemUUID` = `OEM`, see the changelog); the rebuilt stick reached the picker.
2. The picker booted `Install macOS Monterey (external)` to macOS Recovery. Verbose output
   showed the Intel Bluetooth firmware uploading (`ibt-11-5.ddc`).
3. The target was the machine's **only** disk, a 128 GB Toshiba NVMe (`THNSN5128GPU7`) that
   held Windows. The owner chose to replace Windows. The volume, not the device, was erased, so
   the Windows ESP and a `Microsoft Reserved` partition survived.
4. The installer restarted four times. Each restart booted the firmware default, the leftover
   Windows Boot Manager, which showed a blue `winload.efi` / `0xc0000225` recovery screen; F10
   → stick → `macOS Installer` continued the install each time.
5. Once the picker showed `Macintosh HD` instead of `macOS Installer`, that entry booted to the
   Setup Assistant and the desktop. Wi-Fi was greyed out (default build has no Wi-Fi kext).
6. OpenCore was copied to the internal ESP, replacing the Windows boot files, and the NUC now
   boots macOS without the stick. No BIOS boot-order change was needed with a single disk.

Consequences: the reference machine no longer dual-boots, so B-008 and T-DUAL-1…3 don't apply
to it; the installation guide now covers the restart loop, the Windows recovery screen and the
macOS-only disk path; and B-007 needs its formal report (tree digest, `sw_vers`, BIOS version,
T-BOOT-3/4) before "Boots" can become ✅.

## What changed, by phase

| Phase | Status | Main outputs |
| --- | --- | --- |
| 0 Upstream audit | ✅ done (no hardware needed) | [upstream-audit.md](upstream-audit.md): every ACPI table, quirk, device property, kext and script, with a decision and source |
| 1 Hardware inventory | 🟡 tooling done; **data pending** | `scripts/inventory/*`, `skullintosh report --input`, [hardware-inventory.md](hardware-inventory.md), [hardware/reference/nuc6i7kyk.toml](../hardware/reference/nuc6i7kyk.toml) |
| 2 Monterey baseline | 🟡 EFI builds and validates; **boot unverified** | [profiles/monterey](../profiles/monterey), release + debug flavours |
| 3 Build toolkit | ✅ done | `src/skullintosh` (stdlib only), [manifests/dependencies.toml](../manifests/dependencies.toml) |
| 4 USB map | 🟡 generator done; map **provisional** | [usb-mapping.md](usb-mapping.md), [hardware/usb/nuc6i7kyb.toml](../hardware/usb/nuc6i7kyb.toml) |
| 5 Hardware fixes | ⏳ planned per subsystem | [backlog.md](backlog.md), [graphics.md](graphics.md), [hardware-testing.md](hardware-testing.md) |
| 6 Newer macOS | 🟡 research profiles + documented changes | `profiles/{ventura,sonoma,sequoia,tahoe}`, [compatibility.md](compatibility.md) |
| 7 Protect Windows/Linux | ✅ policy, config enforcement, backup scripts; **verification pending** | [windows-linux.md](windows-linux.md), [recovery.md](recovery.md), `scripts/backup/*` |
| 8 CI | 🟡 workflows written; **not yet run on GitHub** | `.github/workflows/ci.yml`, `links.yml` |
| 9 Documentation | ✅ full set | README, docs/*, SECURITY, CONTRIBUTING, CHANGELOG, issue templates |
| 10 Release | ⏳ v0.1.0 ready to tag after first green CI | — |

## Decisions with the biggest consequences

1. **Configs come from the pinned OpenCore release's own `Sample.plist`** plus reviewed overlays,
   with a strict schema check. The binaries, schema and `ocvalidate` therefore always match,
   and a stale key fails the build.
2. **`ResetNvramEntry --preserve-boot`** (enforced). OpenCore's docs say an NVRAM reset
   otherwise deletes other boot options, which here means Windows Boot Manager and GRUB.
3. **`ScanPolicy` 769** hides Windows/Linux from the OpenCore picker, so they're only ever booted
   by the firmware. An opt-in `fat32_installer` mode (2817) exists for FAT32 recovery sticks,
   and the validator still forbids scanning EFI System Partitions and Linux partitions.
4. **`DisableIoMapper`** lets VT-d stay on for Windows/Linux (upstream said to turn it off).
5. **No Apple binaries:** `OpenHfsPlus.efi` instead of `HfsPlus.efi`; no OpenCanopy resources.
6. **Graphics baseline = upstream's last working state** (`0x193B0005` + `device-id 0x1927`),
   minus `enable-hdmi20`, which does nothing on macOS 11+ per WhateverGreen.

## Tests executed (local, macOS arm64 host, Python 3.14)

| Check | Result |
| --- | --- |
| `pytest` (unit: manifest, overlay, profiles, USB map, validator rules, secrets, report sanitizer, utilities, repo hygiene, docs links/backlog IDs) | 74 passed |
| `pytest -m network` (real downloads: Monterey release+debug build, validate, reproducibility, audit decisions present, Wi-Fi variant, research opt-in, tamper detection, deterministic packaging, personal-build refusal) | 7 passed |
| `ocvalidate` 1.0.8 on Monterey release, debug, `wifi=airportitlwm`, `fat32_installer` and all four research profiles | "No issues found" for each |
| Reproducibility | Two clean builds → identical tree digest; two `package` runs → identical zip SHA-256 |
| `ruff check` / `ruff format --check` | clean |
| `skullintosh scan-secrets` | 0 findings |
| `bash -n` on shell scripts | OK |

**Not run locally:** ShellCheck and PSScriptAnalyzer (neither installed here; CI runs both), the
Linux/Windows `ocvalidate` binaries (CI runs the Linux one), the inventory and backup scripts
on real Linux/Windows, and the GitHub Actions workflows themselves (B-095).

## Verified versus untested

| Claim | Status |
| --- | --- |
| Pinned assets match their SHA-256 (GitHub-published digests where they exist; independent re-download otherwise) | verified |
| Generated configs pass OpenCore 1.0.8's `ocvalidate` | verified |
| Builds are reproducible | verified |
| Upstream `OpenCore.efi` isn't an official 0.6.1–0.6.3 build | verified (hash comparison) |
| Monterey EFI boots a NUC6i7KYK | **observed** (12.7.6 installed and booted to the desktop on 2026-10-29, debug flavour); formal report pending |
| Iris Pro 580 acceleration with `0x193B0005`/`0x1927` on Monterey | **untested** (upstream reported it on Catalina) |
| ALC233 codec / layout 32 | **untested** |
| USB map correctness | **untested** (provisional upstream data) |
| `SSDT-EC-USBX` `LPCB` path matches this BIOS | **untested** (upstream booted with it) |
| Ventura+ Kaby Lake spoof gives acceleration on GT4e | **unknown** |
| Windows/Linux unaffected | **not applicable on the reference machine** since 2026-10-29 (macOS-only disk); procedure and enforcement in place for other machines |

## Hardware input needed next (in order)

1. **B-002:** BIOS version, photos of current settings, and both backup scripts run to external
   media.
2. **B-001:** inventory scripts on Linux (with `sudo` for ACPI tables) and Windows;
   `skullintosh report`; confirm the expected IDs (iGPU `193b`, codec `10ec:0233`, I219
   `156f`/`15b7`, 8260 `24f3`/`8087:0a2b`) and record Thunderbolt, SD reader and Super I/O IDs.
3. **B-003:** the DSDT, to confirm `LPCB`/EC/CPU paths.
4. **B-010:** USBToolBox port discovery on Windows.
5. **B-007:** the formal report for the install that already happened: tree digest and
   `provenance.json` of the stick's build, `sw_vers`, BIOS version, T-BOOT-3/4. B-008 no longer
   applies to the reference machine.

## Blockers and risks

| Blocker / risk | Impact | Mitigation |
| --- | --- | --- |
| No formal hardware report yet | Nothing can move past "candidate" even though Monterey boots | Steps above |
| Secure Boot must be off for OpenCore | Weaker boot security for Windows/Linux while testing; possible BitLocker prompt | Documented; re-enable after testing; B-061 |
| The reference machine's only disk now holds macOS | Dual-boot protection can't be exercised there; any future Windows/Linux test needs a second disk or another NUC | Documented; B-008 parked |
| GT4e Kaby Lake spoof viability (Ventura+) is unknown | Newer macOS may need OCLP root patches (SIP/AMFI relaxation) | Research profiles; no silent relaxations |
| No official AirportItlwm for Sequoia/Tahoe | Wi-Fi only via itlwm + HeliPort, or none | Documented |
| Tahoe removed AppleHDA | No analog audio without SIP relaxation | Documented; out of the default path |
| Several GPL dependencies in packages | Source-availability obligations | Unmodified binaries; tags and license texts in every package; THIRD_PARTY_NOTICES |
| Third-party sites changing (Dortania, GitHub release assets) | Broken links; replaced assets | Weekly link check; pinned hashes fail loudly on replaced assets |

# Prioritized backlog

Each item is written to become a GitHub issue. **P0** blocks the Monterey baseline (v0.2.0);
**P1** is needed for a useful daily driver; **P2** improves hardware support; **P3** is research.
🖥 = needs physical access to the NUC. Items without 🖥 can be done by any contributor.

| ID | Pri | 🖥 | Title | Milestone |
| --- | --- | --- | --- | --- |
| [B-001](#b-001) | P0 | 🖥 | Collect and record the reference machine's hardware inventory | v0.2.0 |
| [B-002](#b-002) | P0 | 🖥 | Record BIOS version and original settings; back up boot environment | v0.2.0 |
| [B-003](#b-003) | P0 | 🖥 | Confirm ACPI paths (`LPCB`, CPU scope, `SBUS`) from the DSDT | v0.2.0 |
| [B-007](#b-007) | P0 | 🖥 | First Monterey boot and install on external SSD (debug flavour) | v0.2.0 |
| [B-008](#b-008) | P0 | 🖥 | Verify Windows and Linux are unaffected after first test session | v0.2.0 |
| [B-010](#b-010) | P0 | 🖥 | Build the real USB map with USBToolBox and test it physically | v0.2.0 |
| [B-012](#b-012) | P0 | 🖥 | Iris Pro 580 on Monterey: verify Metal; A/B the `device-id` options | v0.2.0 |
| [B-005](#b-005) | P1 | 🖥 | Booter quirks: check MAT support in the debug log | v0.2.0 |
| [B-006](#b-006) | P1 | 🖥 | CFG Lock state via ControlMsrE2 (read-only) | v0.2.0 |
| [B-050](#b-050) | P1 | 🖥 | Audio: confirm the ALC233 codec and pick the AppleALC layout | v0.2.0 |
| [B-090](#b-090) | P1 | 🖥 | Ethernet I219-LM with IntelMausi | v0.2.0 |
| [B-091](#b-091) | P1 | 🖥 | Bluetooth 8260 on Monterey (pairing, reconnect, sleep) | v0.4.0 |
| [B-092](#b-092) | P1 | 🖥 | Wi-Fi: AirportItlwm vs itlwm on Monterey | v0.4.0 |
| [B-013](#b-013) | P1 | 🖥 | HDMI 2.0 4K60 via the PS175 LSPCON | v0.4.0 |
| [B-030](#b-030) | P1 | 🖥 | Sleep/wake: black screen on wake | v0.4.0 |
| [B-031](#b-031) | P2 | 🖥 | Is `forceRenderStandby=0` still needed? | v0.4.0 |
| [B-016](#b-016) | P2 | 🖥 | Picker keyboard / console output quirks if needed | v0.2.0 |
| [B-017](#b-017) | P2 | 🖥 | `ReleaseUsbOwnership`: needed or not | v0.4.0 |
| [B-020](#b-020) | P2 | 🖥 | CPU power management: measure before adding CPUFriend | v0.4.0 |
| [B-021](#b-021) | P2 | 🖥 | Identify the Super I/O; decide on SMCSuperIO | v0.4.0 |
| [B-022](#b-022) | P2 | 🖥 | NVMeFix: measure benefit on the installed drives | v0.4.0 |
| [B-004](#b-004) | P3 | 🖥 | `SSDT-SBUS-MCHC`: needed or not | v0.4.0 |
| [B-051](#b-051) | P2 | 🖥 | TOSLINK optical output | v0.4.0 |
| [B-061](#b-061) | P2 | | Vault and UEFI Secure Boot signing | v0.4.0 |
| [B-062](#b-062) | P2 | 🖥 | FileVault | v0.4.0 |
| [B-070](#b-070) | P2 | 🖥 | Thunderbolt 3: hot-plug and sleep | v0.4.0 |
| [B-080](#b-080) | P3 | 🖥 | SD card reader: identify controller, evaluate drivers | v0.4.0 |
| [B-040](#b-040) | P1 | 🖥 | Ventura: Kaby Lake spoof for Iris Pro 580 | v0.3.0 |
| [B-041](#b-041) | P3 | 🖥 | Sonoma profile | v0.5.0 |
| [B-042](#b-042) | P3 | 🖥 | Sequoia: graphics path and Wi-Fi | v0.5.0 |
| [B-043](#b-043) | P3 | 🖥 | Tahoe research and security trade-offs | later |
| [B-095](#b-095) | P1 | | First CI run on GitHub; fix any Linux/Windows-only issues | v0.1.0 |
| [B-096](#b-096) | P2 | | Release workflow: attach candidate packages and checksums to tags | v0.2.0 |
| [B-097](#b-097) | P3 | | Optional `iasl` pinning for custom SSDTs | later |

---

## P0: Monterey baseline

### B-001
**Collect and record the reference machine's hardware inventory** · P0 · 🖥 · Phase 1

Run `scripts/inventory/linux-inventory.sh` (with `sudo` for ACPI tables) and
`scripts/inventory/windows-inventory.ps1`; generate `skullintosh report --input …`; fill in
[hardware-inventory.md](hardware-inventory.md).
**Done when:** every "expected" row is confirmed or corrected, and the unknown IDs (Thunderbolt,
SD reader, Super I/O) are recorded.

### B-002
**Record BIOS version and original settings; back up boot environment** · P0 · 🖥 · Phase 7

Photograph or record every BIOS screen listed in [bios-settings.md](bios-settings.md). Run both
backup scripts to external media.
**Done when:** the backups exist off-machine with SHA256SUMS, and the BIOS version is in
hardware-inventory.md.

### B-003
**Confirm ACPI paths from the DSDT** · P0 · 🖥 · Phase 0/2

`SSDT-EC-USBX` assumes `\_SB.PCI0.LPCB`; `SSDT-PLUG` searches the usual CPU scopes. Disassemble
the dumped DSDT (`iasl -d`) and confirm `LPCB` exists, whether an EC device (`H_EC`/`EC0`, PNP0C09)
exists and needs disabling for macOS, and the CPU object names.
**Done when:** findings recorded in upstream-audit.md and the ACPI list confirmed or changed.

### B-007
**First Monterey boot and install** · P0 · 🖥 · Phase 2

Follow [installation.md](installation.md) with the debug flavour. Record T-BOOT-1…4 and attach
the OpenCore log (reviewed).
**Done when:** Monterey installs on the external SSD and cold-boots 5/5, or the blocker is
documented with logs.

### B-008
**Verify Windows and Linux are unaffected** · P0 · 🖥 · Phase 7

Run the "after each test session" checklist in [windows-linux.md](windows-linux.md).
**Done when:** T-DUAL-1…3 pass after B-007. Repeat after every hardware session.

### B-010
**Real USB map** · P0 · 🖥 · Phase 4

Follow [usb-mapping.md](usb-mapping.md) with USBToolBox on Windows; update
`hardware/usb/nuc6i7kyb.toml` with physical labels; run the T-USB-1 table.
**Done when:** all physical ports work at the right speed, Bluetooth works, keyboard works in the
picker, and `verified = true` is set with evidence in the pull request.

### B-012
**Iris Pro 580 on Monterey** · P0 · 🖥 · Phase 5A

Verify acceleration (T-GFX-1…4) with the candidate. Then run experiments G-1 (native `0x193B`),
G-2 (`0x1912`) and G-3 (`enable-metal`) from [graphics.md](graphics.md).
**Done when:** one configuration is chosen on evidence (Metal benchmark, video decode, no crashes
over a week of use) and recorded in graphics.md.

## P1

### B-005
**Booter quirks / MAT** · P1 · 🖥 — Find `OCABC: MAT support is N` and the slide messages in the
debug log; set `SyncRuntimePermissions`/`RebuildAppleMemoryMap`/`ProvideCustomSlide` to match
OpenCore's guidance. **Done when:** the quirk values are justified by log lines.

### B-006
**CFG Lock** · P1 · 🖥 — Run `ControlMsrE2.efi` with no arguments from the debug picker. If
unlocked, drop `AppleXcpmCfgLock`. **Done when:** the result is recorded and the quirk set to
match.

### B-050
**Audio codec and layout** · P1 · 🖥 · Phase 5E — Confirm `10ec:0233` (Linux
`/proc/asound/card*/codec#0`, Windows `HDAUDIO\…DEV_0233`). Test layout 32, then other ALC233
layouts in AppleALC 1.9.8 (3, 4, 5, 13, 21, 27, 28, 29, 33) for headphone, mic and line paths (T-AUD-1/2/5).
**Done when:** a layout is chosen on evidence.

### B-090
**Ethernet** · P1 · 🖥 — T-NET-1 with IntelMausi; record the I219 device ID (`156f` vs `15b7`).

### B-091
**Bluetooth** · P1 · 🖥 · Phase 5F — T-BT-1/2/3 with IntelBluetoothFirmware + IntelBTPatcher +
BlueToolFixup. Confirm the USB port (HS09?) and its internal type in the map.

### B-092
**Wi-Fi** · P1 · 🖥 · Phase 5F — Compare `--set wifi=airportitlwm` and `--set wifi=itlwm`
(+HeliPort) on T-WIFI-1/2 and T-BT-3. The validator already prevents loading both.
**Done when:** a recommended default is chosen per macOS version.

### B-013
**HDMI 2.0 / LSPCON** · P1 · 🖥 · Phase 5A — T-GFX-5…9 with and without G-4/G-5. WhateverGreen
names the Skull Canyon's PS175 LSPCON; upstream dropped LSPCON support for stability.

### B-030
**Sleep / wake black screen** · P1 · 🖥 · Phase 5B — Reproduce T-PWR-2 with the baseline. Then
vary one at a time: `force-online`, `disable-agdc`, LSPCON, which display port is used, the USB
map's wake behaviour, `pmset` settings (hibernatemode 0, standby 0, tcpkeepalive 0), and
HibernationFixup. Gather `pmset -g log` and wake reasons. **Done when:** 10/10 wakes restore the
display, or the cause is documented.

### B-040
**Ventura graphics** · P1 · 🖥 · Phase 6 — Only after B-012. Test KBL-A and KBL-B from
graphics.md with T-GFX-1…4. **Done when:** a spoof gives Metal acceleration, or the result is
documented as not possible without OCLP.

### B-095
**First CI run** · P1 — Push to GitHub and make `.github/workflows/ci.yml` pass (ShellCheck and
PSScriptAnalyzer haven't been run locally yet). **Done when:** CI is green on `main`.

## P2

### B-016
**Picker input/output** · P2 · 🖥 — Only if the picker has no keyboard or no display: try
`OpenUsbKbDxe`, `KeySupport`, `ProvideConsoleGop`, and `UEFI/Output` options, one at a time.

### B-017
**ReleaseUsbOwnership** · P2 · 🖥 — Upstream enabled it. Check whether USB devices fail early
in boot without it.

### B-020
**CPU power management** · P2 · 🖥 · Phase 5G — Measure idle frequency, package power and turbo
with `powermetrics` (T-PWR-1/4). Add CPUFriend + a generated data provider only if the
measurements show a problem.

### B-021
**Super I/O / fans** · P2 · 🖥 — Identify the chip; try `SMCSuperIO` only if it is supported.

### B-022
**NVMeFix** · P2 · 🖥 — T-NVME-1 on the actual drives (`--set nvmefix=true`).

### B-031
**forceRenderStandby** · P2 · 🖥 — After a stable baseline, remove it (G-7) and run a week of
idle/sleep cycles watching for NVMe panics.

### B-051
**TOSLINK** · P2 · 🖥 — Upstream said "disabled in SSDT", but no such SSDT exists in the archive.
Test whether any ALC233 layout exposes the optical output (T-AUD-4).

### B-061
**Vault and Secure Boot** · P2 — Evaluate OpenCore Vault (`Secure`) for the release flavour, and
UEFI Secure Boot with self-enrolled keys (signing OpenCore and drivers). This must not break the
Windows/Linux Secure Boot chain. Design document first.

### B-062
**FileVault** · P2 · 🖥 — T-FV-1. Revisit `ProtocolOverrides` only on failure.

### B-070
**Thunderbolt 3** · P2 · 🖥 · Phase 5C — Record the Alpine Ridge IDs and firmware version
(Windows Thunderbolt software). Test T-TB-1…3 with BIOS security "Legacy". Research
Skull Canyon-specific ACPI (not Hades Canyon patches without verifying the controller). Firmware
flashing is **out of scope**.

### B-096
**Release workflow** · P2 — A tag-triggered workflow that builds, validates and attaches
`skullintosh package` output and `.sha256` files to a GitHub release as **candidate** (not
"verified") unless a hardware report is linked.

## P3

### B-004
**SSDT-SBUS-MCHC** · P3 · 🖥 — After B-003 confirms `SBUS`, test whether AppleSMBus benefits.

### B-041
**Sonoma** · P3 · 🖥 — After Ventura. SMBIOS iMac19,1 vs MacBookAir8,1; AirportItlwm 14.0/14.4.

### B-042
**Sequoia** · P3 · 🖥 — Is a Kaby Lake framebuffer still usable? Wi-Fi via itlwm + HeliPort only.

### B-043
**Tahoe** · P3 · 🖥 — Document which OCLP root patches (if any) would give graphics and audio,
and the SIP/AMFI/Secure Boot relaxations each needs. No relaxed profile without an explicit,
recorded decision.

### B-080
**SD card reader** · P3 · 🖥 · Phase 5D — Record the controller's PCI ID. If it's a Realtek
PCIe reader, evaluate 0xFireWolf/RealtekCardReader (last release v0.9.7, 2022; a third-party
owner, so it would need adding to `approved_owners`). Otherwise document as unsupported.

### B-097
**iasl pinning** · P3 — If custom SSDTs become necessary, pin an ACPICA `iasl` version and
check compiled AML in CI.

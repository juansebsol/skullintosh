# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/). Release names (v0.2.0 "Monterey baseline", …) are
goals, not compatibility promises.

## [Unreleased] - v0.1.0 "Foundation"

### Added

* Upstream audit of `alexpotter1/intel-nuc6i7kyk-opencore` @ `2ccbf26` with a decision for
  every inherited component (`docs/upstream-audit.md`).
* `skullintosh` CLI (Python 3.11+, stdlib only): `doctor`, `fetch`, `pin`, `build`, `validate`,
  `package`, `report`, `scan-secrets`, `profiles`.
* Dependency manifest pinning OpenCore 1.0.8, Lilu 1.7.2, WhateverGreen 1.7.1, AppleALC 1.9.8,
  VirtualSMC 1.3.8, IntelMausi 1.0.8, NVMeFix 1.1.3, BrcmPatchRAM 2.7.2 (BlueToolFixup),
  IntelBluetoothFirmware v2.4.0, itlwm v2.3.0, all by SHA-256.
* Monterey profile (status **candidate**, unverified on hardware): `iMac17,1`, Iris Pro 580
  framebuffer `0x193B0005`, codeless USB map (provisional, from upstream data), optional
  Bluetooth/Wi-Fi/NVMeFix, release and debug flavours.
* Research profiles for Ventura, Sonoma, Sequoia and Tahoe (build only with `--allow-research`).
* Validator: file references, kext dependency/order/version, Wi-Fi exclusivity, per-OS kext
  applicability, SIP/Secure Boot relaxations, dual-boot safety (`LauncherOption`,
  `RequestBootVarRouting`, `ScanPolicy`, `ResetNvramEntry --preserve-boot`), SMBIOS leaks,
  post-build tampering, matching `ocvalidate`.
* Reproducible builds and deterministic release zips with provenance and license texts.
* Read-only hardware inventory and boot-backup scripts for Linux and Windows; sanitized
  reporting with reconciliation against expected device IDs.
* Documentation set, issue templates, CI (lint, tests, end-to-end builds, ocvalidate,
  reproducibility, secret scan) and a weekly link check.
* Record of the first hardware session (2026-10-28/29): Monterey 12.7.6 installs and boots on
  the reference NUC from the debug flavour. The installation guide now covers the F10 menu's
  legacy/UEFI entries, the installer's restart loop, the leftover Windows Boot Manager screen
  (`winload.efi`, `0xc0000225`), the Setup Assistant, and the macOS-only disk path (OpenCore on
  the internal ESP). Troubleshooting, compatibility, inventory and backlog updated to match.

### Fixed

* Shared builds halted in OpenCore with `Grabbed zero system-id for SB` (found on the first
  hardware boot). They now set `PlatformInfo/Generic/SystemUUID` to `OEM` so Apple Secure Boot
  uses the firmware's own UUID; a new `secure-boot-id` validator rule catches a zero UUID with
  Secure Boot on, and `--smbios` identities can no longer use the zero UUID.

### Changed from upstream (see the audit for reasons)

* OpenCore binaries from official releases instead of a committed nightly build.
* `ssdtPRgen` CPU tables + CPUFriend → OpenCore `SSDT-PLUG`.
* USBInjectAll + `SSDT-UIAC` → generated codeless USB map.
* IntelMausiEthernet → IntelMausi; IntelBluetoothInjector → BlueToolFixup + IntelBTPatcher.
* `VBoxHfs.efi` → `OpenHfsPlus.efi` (no Apple binaries).
* `SecureBootModel` Disabled → Default; `ScanPolicy` 0 → 769.
* Removed `enable-hdmi20` (no-op on macOS 11+), `enable-metal`, cosmetic device properties and
  the conflicting second audio `layout-id`.

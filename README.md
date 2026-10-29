# Skullintosh

Reproducible, validated OpenCore builds for the **Intel NUC6i7KYK "Skull Canyon"**.

Skullintosh continues the archived
[alexpotter1/intel-nuc6i7kyk-opencore](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore)
project (last updated in 2020 for Catalina/Big Sur beta). It does not ship a downloaded EFI
folder. It ships a small Python tool that builds one from pinned, checksum-verified official
releases, validates it, and records where every byte came from.

> [!WARNING]
> **Monterey installs and boots on a real NUC6i7KYK, but isn't verified yet.** On 2026-10-29
> the debug build installed macOS 12.7.6 on the reference machine, which now boots it from its
> internal disk. Graphics acceleration, audio, USB, sleep and Wi-Fi haven't been tested, so the
> profile stays a *candidate* until the core
> [hardware tests](docs/hardware-testing.md#core-required-for-verified) pass. CI passing is
> not evidence that anything works. See [docs/compatibility.md](docs/compatibility.md) for
> exactly what is known.

## Status

| macOS | Profile | Status | Notes |
| --- | --- | --- | --- |
| 12 Monterey | `monterey` | **candidate** (installs and boots; core tests pending) | Baseline: native Skylake graphics, `iMac17,1` |
| 13 Ventura | `ventura` | research | Needs a Kaby Lake graphics spoof; not yet known to accelerate Iris Pro 580 |
| 14 Sonoma | `sonoma` | research | Starts after Ventura |
| 15 Sequoia | `sequoia` | research | No official AirportItlwm build; graphics path unknown |
| 26 Tahoe | `tahoe` | research (experimental) | AppleHDA removed; analog audio needs SIP relaxation |

Research profiles only build with `--allow-research` and are never packaged. macOS 27 is out of
scope because it doesn't support Intel Macs.

## Hardware

Intel NUC6i7KYK (board NUC6i7KYB): Core i7-6770HQ, Iris Pro Graphics 580, I219-LM Ethernet,
Wireless-AC 8260 + Bluetooth, Realtek ALC233 (per upstream; unconfirmed), two M.2 slots,
HDMI 2.0, Mini DisplayPort, Thunderbolt 3 (USB-C), SDXC. Expected IDs are in
[hardware/reference/nuc6i7kyk.toml](hardware/reference/nuc6i7kyk.toml). Other NUC models are
not supported: their USB maps, framebuffers and ACPI differ.

## Quick start (building only; this does not touch your disks)

Requires Python 3.11+. Works on macOS, Linux and Windows.

```bash
git clone https://github.com/juansebsol/skullintosh && cd skullintosh
python3 -m venv .venv && . .venv/bin/activate
pip install -e .
skullintosh doctor
skullintosh build --target monterey            # -> build/monterey-release/EFI
skullintosh build --target monterey --flavor debug
```

Optional features: `--set wifi=airportitlwm` (or `itlwm`), `--set bluetooth=false`,
`--set nvmefix=true`. Your SMBIOS identity is applied only from a git-ignored local file:
`--smbios local/smbios.toml` (see [docs/installation.md](docs/installation.md)).

Before booting anything, read **[docs/installation.md](docs/installation.md)**,
**[docs/windows-linux.md](docs/windows-linux.md)** and **[docs/recovery.md](docs/recovery.md)**.
The supported way to test is from a **removable USB stick**, choosing it in the firmware's F10
boot menu. Your existing Windows and Linux boot entries stay untouched.

## What the tool guarantees

* Every binary comes from an official GitHub release by an approved owner (acidanthera,
  OpenIntelWireless) and must match a pinned SHA-256.
* OpenCore binaries, drivers, sample ACPI tables, `Sample.plist` and `ocvalidate` all come from
  the **same** release archive.
* `config.plist` is generated from that release's `Sample.plist` plus small reviewed overlays.
  A key that doesn't exist in that OpenCore version's schema fails the build.
* Validation checks: file references, kext dependencies and load order, Wi-Fi kext
  exclusivity, per-macOS kext applicability, SIP/Secure Boot relaxations, dual-boot safety
  (boot-order protection, `ScanPolicy`, NVRAM-reset behaviour), SMBIOS leaks, tampering after
  the build, and `ocvalidate`.
* Identical inputs give byte-identical outputs and release zips.
* Nothing writes to an EFI System Partition, edits partitions, or changes UEFI boot entries.

## Documentation

| | |
| --- | --- |
| [installation.md](docs/installation.md) | Building, installer media, first boot from USB |
| [bios-settings.md](docs/bios-settings.md) | Firmware settings and how to roll them back |
| [windows-linux.md](docs/windows-linux.md) | Keeping the existing dual-boot safe |
| [recovery.md](docs/recovery.md) | Restoring the original boot environment |
| [compatibility.md](docs/compatibility.md) | Per-version, per-subsystem status and evidence |
| [hardware-inventory.md](docs/hardware-inventory.md) | Collecting and recording hardware IDs |
| [hardware-testing.md](docs/hardware-testing.md) | Physical test procedures |
| [graphics.md](docs/graphics.md) | Iris Pro 580 configuration and experiments |
| [usb-mapping.md](docs/usb-mapping.md) | Building the real USB map |
| [troubleshooting.md](docs/troubleshooting.md) | Common boot failures |
| [upstream-audit.md](docs/upstream-audit.md) | Every inherited setting, with a decision |
| [backlog.md](docs/backlog.md) | Prioritized work items |
| [development.md](docs/development.md) | Contributor setup and repository layout |
| [progress-report.md](docs/progress-report.md) | Current status, evidence and blockers |

## Legal

Skullintosh is MIT-licensed. Third-party components keep their own licenses
([THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)). No Apple software is included. macOS is
licensed by Apple for Apple-branded hardware; you are responsible for complying with Apple's
license terms. This project is for research, education and interoperability work.

Credits: Alex Potter (upstream project), acidanthera (OpenCore, Lilu, WhateverGreen, AppleALC,
VirtualSMC, IntelMausi, NVMeFix, BrcmPatchRAM), OpenIntelWireless (itlwm,
IntelBluetoothFirmware), Dortania (guides), CorpNewt (GenSMBIOS, SSDTTime), USBToolBox, and
RehabMan's original Skull Canyon work.

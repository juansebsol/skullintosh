# Skullintosh

Reproducible, validated OpenCore builds for the **Intel NUC6i7KYK "Skull Canyon"**.

Skullintosh doesn't ship a ready-made EFI folder. It ships a small Python tool that builds one
from pinned, checksum-verified official releases, checks it, and records where every file came
from. It continues the archived
[alexpotter1/intel-nuc6i7kyk-opencore](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore)
(2020, Catalina) on current OpenCore and macOS.

## Status

| macOS | Profile | Status |
| --- | --- | --- |
| 12 Monterey | `monterey` | **candidate**: installs and boots on the reference NUC; Wi-Fi and Bluetooth firmware work; core hardware tests pending |
| 13 Ventura | `ventura` | research: needs a Kaby Lake graphics spoof, unproven on Iris Pro 580 |
| 14 Sonoma | `sonoma` | research |
| 15 Sequoia | `sequoia` | research: Wi-Fi only via itlwm + HeliPort |
| 26 Tahoe | `tahoe` | research: no analog audio without SIP relaxation |

A profile becomes **verified** only when the [core hardware tests](docs/hardware-testing.md)
pass on a NUC6i7KYK. CI only proves that a build is well-formed. Research profiles build only
with `--allow-research` and are never packaged. macOS 27 is out of scope (no Intel support).
Per-feature status: [compatibility.md](docs/compatibility.md).

## Hardware

NUC6i7KYK (board NUC6i7KYB): Core i7-6770HQ, Iris Pro 580, I219-LM Ethernet, Wireless-AC 8260 +
Bluetooth, Realtek ALC233 (unconfirmed), two M.2 slots, HDMI 2.0, Mini DisplayPort, Thunderbolt 3, SDXC. Other
NUC models aren't supported: their USB maps, graphics and ACPI differ.

## Install

Follow **[docs/installation.md](docs/installation.md)**. It builds the EFI, makes a USB
installer on a Mac, installs macOS, and makes the disk boot on its own.

To build without installing anything (Python 3.11+, macOS, Linux or Windows):

```bash
git clone https://github.com/juansebsol/skullintosh && cd skullintosh
python3 -m venv .venv && . .venv/bin/activate
pip install -e .
skullintosh build --target monterey --set wifi=airportitlwm   # -> build/monterey-release/EFI
```

Build options: `--flavor debug`, `--set wifi=none|airportitlwm|itlwm`, `--set bluetooth=false`,
`--set nvmefix=true`, `--smbios local/smbios.toml`.

## What the tool guarantees

* Binaries come only from official releases by approved owners (acidanthera,
  OpenIntelWireless) and must match a pinned SHA-256.
* `config.plist` is generated from the pinned OpenCore release's own `Sample.plist` plus small
  reviewed overlays, then checked with that release's `ocvalidate` and Skullintosh's rules
  (kext order, Secure Boot and SIP, boot-order and dual-boot safety, serial-number leaks).
* The same inputs always produce byte-identical output.
* The tool never writes to EFI partitions or changes firmware boot entries. Copying the EFI is
  always a manual step.

## Documentation

**Using it**

| | |
| --- | --- |
| [installation.md](docs/installation.md) | Full install, booting without the stick, updating the EFI |
| [wifi.md](docs/wifi.md) | Wi-Fi driver options and adding Wi-Fi to an installed system |
| [apple-services.md](docs/apple-services.md) | Optional: your own serial for Apple ID, iCloud, iMessage |
| [bios-settings.md](docs/bios-settings.md) | Firmware settings and rolling them back |
| [troubleshooting.md](docs/troubleshooting.md) | Boot failures by stage |
| [recovery.md](docs/recovery.md) | Getting a machine back to booting |
| [windows-linux.md](docs/windows-linux.md) | Keeping Windows or Linux on the same machine |
| [compatibility.md](docs/compatibility.md) | What works, per macOS version and per feature |
| [hardware-testing.md](docs/hardware-testing.md) | Test procedures for reporting results |

**Developing it** ([docs/dev/](docs/dev/))

| | |
| --- | --- |
| [development.md](docs/dev/development.md) | Setup, repository layout, how a build works |
| [backlog.md](docs/dev/backlog.md) | Prioritized work items |
| [progress-report.md](docs/dev/progress-report.md) | Current status, evidence and blockers |
| [upstream-audit.md](docs/dev/upstream-audit.md) | Every setting inherited from upstream, with a decision |
| [graphics.md](docs/dev/graphics.md) | Iris Pro 580 configuration and experiments |
| [usb-mapping.md](docs/dev/usb-mapping.md) | Building the real USB map |
| [hardware-inventory.md](docs/dev/hardware-inventory.md) | Collecting and recording hardware IDs |

Contributing: [CONTRIBUTING.md](CONTRIBUTING.md). Security: [SECURITY.md](SECURITY.md).

## Legal

MIT-licensed. Third-party components keep their own licenses
([THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)). No Apple software is included. macOS is
licensed by Apple for Apple-branded hardware; you are responsible for complying with Apple's
license terms. This project is for research, education and interoperability work.

Credits: Alex Potter (upstream project), acidanthera (OpenCore, Lilu, WhateverGreen, AppleALC,
VirtualSMC, IntelMausi, NVMeFix, BrcmPatchRAM), OpenIntelWireless (itlwm,
IntelBluetoothFirmware), Dortania (guides), CorpNewt (GenSMBIOS, SSDTTime), USBToolBox, and RehabMan's
original Skull Canyon work.

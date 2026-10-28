# Hardware inventory

This page has two parts: **how to collect** identifiers safely, and the **record** of what the
project's reference machine actually reports. The record is empty until someone runs the
scripts on real hardware. Expected values come from
[hardware/reference/nuc6i7kyk.toml](../hardware/reference/nuc6i7kyk.toml).

## Collecting (read-only)

| OS | Command | Needs admin? |
| --- | --- | --- |
| Linux | `scripts/inventory/linux-inventory.sh OUTDIR` | No (adds dmidecode and ACPI tables when run with `sudo`) |
| Windows | `powershell -ExecutionPolicy Bypass -File scripts\inventory\windows-inventory.ps1 -OutputDir OUTDIR` | No (adds firmware boot entries when elevated) |

What they collect: DMI product/board/BIOS strings, CPU model and flags, `lspci -nnk` /
PnP PCI IDs, USB IDs and topology, HDA codec vendor/device, Thunderbolt devices, disk models and
partition types, UEFI boot entries, and (Linux + root) raw ACPI tables for SSDT work.

What they **don't** collect: serial numbers (filtered at the source), MAC addresses, system
UUIDs, Wi-Fi networks, user names or product keys. The Windows licensing tables `MSDM`/`SLIC`
are skipped.

Then make a shareable report:

```bash
skullintosh report --input OUTDIR --output inventory-report.md
```

The report masks anything identifying that slipped through (serials, UUIDs other than public
GPT/NVRAM GUIDs, MACs, IPs, USB instance serials, home-directory names, product keys) and
reconciles the IDs it finds against the expected hardware. **Read it before sharing**: automatic
masking is a safety net, not a guarantee. Raw output and ACPI tables stay on your machine and
are git-ignored (`inventory-raw*/`, `local/`).

## Reconciliation with Intel's specification

| Subsystem | Intel spec / upstream | Expected ID | Observed on reference machine | Status |
| --- | --- | --- | --- | --- |
| Board | NUC6i7KYB | — | _pending_ | ❓ |
| BIOS version | KYSKLi70.86A.xxxx | — | _pending_ | ❓ |
| CPU | i7-6770HQ, 4C/8T, Skylake-H (CPUID 0x506E3) | — | _pending_ | ❓ |
| iGPU | Iris Pro 580 (GT4e, 128 MB eDRAM) | `8086:193b` | _pending_ | ❓ |
| PCH | HM170 | LPC `8086:a14e` | _pending_ | ❓ |
| xHCI | 100 Series | `8086:a12f` | _pending_ | ❓ |
| HD Audio | 100 Series HDA | `8086:a170` | _pending_ | ❓ |
| Codec | Realtek ALC233 (upstream; not on Intel's spec sheet) | `10ec:0233` | _pending_ | ❓ |
| Ethernet | Intel I219-LM | `8086:156f` or `8086:15b7` | _pending_ | ❓ |
| Wi-Fi | Intel Dual Band Wireless-AC 8260 | `8086:24f3` | _pending_ | ❓ |
| Bluetooth | Intel 8260 BT (USB) | `8087:0a2b` | _pending_ | ❓ |
| Thunderbolt 3 | Intel Alpine Ridge (JHL6540) | to record | _pending_ | ❓ |
| SDXC reader | PCIe reader (upstream) | to record | _pending_ | ❓ |
| Super I/O / EC | unknown | to record | _pending_ | ❓ |
| M.2 slot 1 / 2 | NVMe/SATA M.2 | model only | _pending_ | ❓ |
| Display outputs | HDMI 2.0 (Parade PS175 LSPCON per WhateverGreen), Mini DP 1.2, USB-C DP via TB3 | — | _pending_ | ❓ |

## UEFI boot entries (names only)

| Entry | Disk | Notes |
| --- | --- | --- |
| _pending_ | | |

## Disk layout (no serials)

| Slot | Model | OS | Partition style | ESP size |
| --- | --- | --- | --- | --- |
| M.2 #1 | _pending_ | Windows / Linux | | |
| M.2 #2 | _pending_ | Windows / Linux | | |

## BIOS settings as found

Record the values *before* any change in [bios-settings.md](bios-settings.md).

## How to update this page

1. Run the scripts and `skullintosh report`.
2. Copy only the IDs and model names (never serials) into the tables above.
3. If an ID differs from the expected one, update
   [hardware/reference/nuc6i7kyk.toml](../hardware/reference/nuc6i7kyk.toml) in the same pull
   request and say where the difference came from.

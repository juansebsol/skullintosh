# Compatibility matrix

**Rule:** a cell says *works* only with a linked hardware test report (issue or
[hardware-testing.md](hardware-testing.md) record) naming the build's `provenance.json` tree
digest. CI results never count.

Legend: **✅ verified** · **🟡 expected** (documented upstream or by Dortania/acidanthera, not yet
tested here) · **❓ unknown** · **⛔ known broken / unsupported** · **— not applicable**

_Last updated: 2026-10-29. Hardware sessions so far: one informal session on 2026-10-28/29
(Monterey 12.7.6, debug flavour, reference NUC). No formal test report with a tree digest yet, so
no cell is ✅._

## By macOS version

| | 12 Monterey | 13 Ventura | 14 Sonoma | 15 Sequoia | 26 Tahoe |
| --- | --- | --- | --- | --- | --- |
| Profile status | candidate | research | research | research | research |
| SMBIOS | `iMac17,1` | `iMac18,1` | `iMac19,1` | `iMac19,1` | `iMac20,1` |
| Boots | 🟡 installed and booted to the desktop on 2026-10-29 (12.7.6, debug flavour, internal NVMe); T-BOOT-3/4 and the report are pending | ❓ | ❓ | ❓ | ❓ |
| iGPU acceleration (Metal) | 🟡 native SKL drivers; upstream reported Metal on Catalina | ❓ needs KBL spoof (B-040) | ❓ | ❓ (B-042) | ❓ likely needs OCLP root patches (B-043) |
| HDMI 2.0 4K60 | ❓ (B-013) | ❓ | ❓ | ❓ | ❓ |
| Mini DisplayPort | 🟡 | ❓ | ❓ | ❓ | ❓ |
| USB-C / TB3 DisplayPort | ❓ | ❓ | ❓ | ❓ | ❓ |
| Multi-monitor | 🟡 upstream | ❓ | ❓ | ❓ | ❓ |
| Analog audio (ALC233) | 🟡 layout 32 (B-050) | 🟡 | 🟡 | 🟡 | ⛔ AppleHDA removed (Dortania) |
| HDMI/DP audio | ❓ | ❓ | ❓ | ❓ | 🟡 unaffected per Dortania |
| TOSLINK optical | ❓ (B-051) | ❓ | ❓ | ❓ | ⛔ |
| Ethernet I219-LM | 🟡 IntelMausi | 🟡 | 🟡 | 🟡 | ❓ |
| Wi-Fi AC 8260 | 🟡 AirportItlwm (Monterey build): joined a network and stayed connected on 2026-10-29 (informal); throughput and sleep untested | 🟡 AirportItlwm (Ventura build) | 🟡 AirportItlwm (14.0 / 14.4 builds) | 🟡 itlwm + HeliPort only | ❓ itlwm untested on 26 |
| Bluetooth | 🟡 IntelBluetoothFirmware + BlueToolFixup; the verbose installer boot showed the firmware upload (`ibt-11-5.ddc`, "Firmware download done"); pairing untested | 🟡 | 🟡 | 🟡 | 🟡 needs `-ibtcompatbeta` |
| USB map | ❓ provisional (B-010) | ❓ | ❓ | ❓ | ❓ |
| Sleep / wake | ⛔ upstream: black screen on wake (B-030) | ❓ | ❓ | ❓ | ❓ |
| Thunderbolt 3 hot-plug | ⛔ upstream: boot-time only (B-070) | ❓ | ❓ | ❓ | ❓ |
| SDXC reader | ⛔ upstream: unsupported (B-080) | ⛔ | ⛔ | ⛔ | ⛔ |
| CPU power management | 🟡 XCPM via SSDT-PLUG | 🟡 | 🟡 | 🟡 | 🟡 |
| NVMe | 🟡 native | 🟡 | 🟡 | 🟡 | 🟡 |
| FileVault | ❓ (B-062) | ❓ | ❓ | ❓ | ❓ |
| Windows/Linux untouched after testing | — on the reference machine since 2026-10-29 (its only disk is macOS-only by the owner's decision); ❓ for any machine that keeps other OSes ([windows-linux.md](windows-linux.md)) | | | | |

## Why each newer version is harder

| Version | What changes for this machine | Source |
| --- | --- | --- |
| 13 Ventura | Skylake graphics drivers removed: spoof Iris Pro 580 as Kaby Lake (WhateverGreen ≥ 1.6.1). `iMac17,1` dropped → `iMac18,1`. AVX2 needed (i7-6770HQ has it). | Dortania extras/ventura.md; WhateverGreen FAQ.IntelHD |
| 14 Sonoma | `iMac18,1` dropped (last OS 13.6.x). AirportItlwm split at 14.4. | Dortania smbios-support.md; itlwm v2.3.0 release |
| 15 Sequoia | No AirportItlwm release; only itlwm + HeliPort. Whether Kaby Lake graphics drivers remain usable is unverified. | itlwm v2.3.0 release assets |
| 26 Tahoe | Only `MacBookPro16,x`, `MacPro7,1`, `iMac20,x` supported. AppleHDA removed (AppleALC analog audio gone; the VoodooHDA workaround needs `csr-active-config 03000000`). Intel Bluetooth needs `-ibtcompatbeta`. Last Intel release. | Dortania extras/tahoe.md |
| 27 | No Intel support. Out of scope. | — |

## Security-reducing patches

Skullintosh's validator **rejects** any configuration that:

* sets `csr-active-config` to anything but `00000000` (SIP fully on),
* adds AMFI or compatibility-check bypass boot arguments (`amfi_get_out_of_my_way`, `amfi=`,
  `-no_compat_check`, `ipc_control_port_options`, …),
* sets `SecureBootModel` to `Disabled`, or `DmgLoading` to `Any`.

OpenCore Legacy Patcher root patches (likely needed for Iris Pro 580 acceleration on newer macOS,
and VoodooHDA on Tahoe) need SIP partly disabled, AMFI changes on some versions, and a broken
system-volume seal. Effects: no delta OS updates, a weaker defence against persistent malware,
and re-patching after every update. If the project ever supports such a configuration, it will
be a separate, clearly named profile with a documented decision, never a silent default.
Tracked in [B-043](dev/backlog.md#b-043).

## Reporting results

Use the **Compatibility test report** issue template. Include `provenance.json` (it contains no
personal data unless you built with `--smbios`, which is recorded only as
`"personalized": true`) and the sanitized output of `skullintosh report`.

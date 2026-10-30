# Upstream audit: `alexpotter1/intel-nuc6i7kyk-opencore`

This document records every component Skullintosh inherited (or chose not to inherit) from the
archived Skull Canyon OpenCore project, and why.

| Item | Value |
| --- | --- |
| Upstream repository | <https://github.com/alexpotter1/intel-nuc6i7kyk-opencore> |
| Audited commit | [`2ccbf26`](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore/commit/2ccbf269982088848a1176ea2bda8b9e2a031184) "Archive repository" (2020-11-10) |
| History | 44 commits, 2020-03-02 → 2020-11-10 |
| License | MIT, © 2020 Alex Potter (retained in [`LICENSE`](../../LICENSE) and [`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md)) |
| Last OS the author reported | macOS Big Sur **beta** (README); Catalina screenshot |
| Audit date | 2026-10-28 |
| Compared against | OpenCorePkg 1.0.8 `Sample.plist` + `Configuration.pdf`, WhateverGreen 1.7.1 manual, Dortania OpenCore Install Guide (desktop + laptop Skylake pages, Ventura page), AppleALC master, zearp/Nucintosh @ `c8de99f` (2026-10-11) |

**Decision key:** **Retain** = carried forward unchanged in intent · **Replace** = same goal, modern
mechanism · **Remove** = not carried forward · **Investigate** = needs hardware evidence; tracked in
[`docs/backlog.md`](backlog.md) with the ID shown.

> Nothing in this audit has been verified on hardware by this project yet. "Upstream evidence"
> means the upstream author reported it on their own NUC6i7KYK in 2020 on Catalina/Big Sur beta.

---

## 1. OpenCore version and schema

| Finding | Evidence | Decision |
| --- | --- | --- |
| The upstream `OpenCore.efi` (SHA-256 `1a1a301b…aa95d`, 473,152 bytes) does **not** match the official 0.6.1, 0.6.2 or 0.6.3 RELEASE builds, nor the 0.6.2 or 0.6.3 DEBUG builds. It was most likely a nightly from around 0.6.2. | Hashes compared against the official release zips during this audit; [`6fe5b67`](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore/commit/6fe5b6767ef1894236a1fea304178726580ef89c) "Update OpenCore" is dated 2020-10-17 | **Remove** all upstream binaries. Skullintosh downloads official OpenCorePkg releases only, pinned by SHA-256 ([`manifests/dependencies.toml`](../../manifests/dependencies.toml)). |
| The config schema is from the 0.6.x era: it has `ApECID`/`SecureBootModel` (added in 0.6.1), but lacks the `UEFI/Audio`, `UEFI/AppleInput`, `Kernel/Add/*/Arch`, `Misc/Boot/LauncherOption` and `Booter/Patch` keys that 1.0.8 requires. | `ocvalidate` 1.0.8 would reject it; compare with 1.0.8 `Docs/Sample.plist` | **Replace**: configs are generated from the pinned release's own `Sample.plist` plus small reviewed overlays, so the schema always matches the binaries and the matching `ocvalidate`. |
| `Bootstrap/Bootstrap.efi` | Removed from OpenCore in 0.6.6 (replaced by `LauncherOption`) | **Remove**. `LauncherOption` stays `Disabled`, so OpenCore never registers itself in the firmware boot order (see [windows-linux.md](../windows-linux.md)). |
| `Tools/VerifyMsrE2.efi`, `Tools/CleanNvram.efi` | `VerifyMsrE2` was renamed `ControlMsrE2`; NVRAM reset is now the `ResetNvramEntry.efi` driver | **Replace**: debug builds ship `ControlMsrE2.efi` (read-only use documented); release builds use `ResetNvramEntry.efi`. |
| `Drivers/VBoxHfs.efi` | Dropped from OpenCore; OpenCore 1.0.8 ships the open-source `OpenHfsPlus.efi` | **Replace** with `OpenHfsPlus.efi`. Skullintosh deliberately does **not** use Apple's proprietary `HfsPlus.efi` from OcBinaryData (no Apple binaries are bundled). |
| `Drivers/AppleGenericInput.efi` | Merged into OpenCore as `UEFI/AppleInput` / `OpenUsbKbDxe` | **Remove**. The firmware's own keyboard support is the default; revisit only if the picker can't read the keyboard ([B-016](backlog.md)). |
| `Drivers/OpenCanopy.efi` + `Resources/` (Apple icons from OcBinaryData) | Cosmetic; the resources are Apple artwork | **Remove**. Builtin text picker. Users can add OpenCanopy themselves. |

## 2. ACPI

Upstream shipped `.dsl` sources and compiled them at setup time with RehabMan's 2016 `iasl61`
fork from Bitbucket (`build_acpi.sh`), a URL that no longer resolves reliably.

| Table | Origin and purpose | Current guidance | Decision |
| --- | --- | --- | --- |
| `SSDT-EC-USBX.dsl` (`ACDT`/`SsdtEC`) | Byte-identical intent to OpenCore's sample, adopted upstream in [`2c575fe`](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore/commit/2c575fe95c9484ff26236a03fa8cd914f85e8053). Creates a fake `EC` under `\_SB.PCI0.LPCB` and a `USBX` power-properties device, both `_OSI("Darwin")`-gated. | Still required on Catalina+ for desktops ([Dortania: Getting Started With ACPI](https://dortania.github.io/Getting-Started-With-ACPI/)). The OpenCore 1.0.8 source `Docs/AcpiSamples/Source/SSDT-EC-USBX.dsl` is the same table. | **Retain**, using the precompiled `SSDT-EC-USBX.aml` from the pinned OpenCore release (checksummed; no `iasl` needed). The `LPCB` path assumption still has to be confirmed against this machine's DSDT ([B-003](backlog.md)). |
| `SSDT-SBUS-MCHC.dsl` | OpenCore sample. Adds `MCHC` and an SMBus `BUS0`/`DVL0` device for AppleSMBus. Also declares a stray `DTGP` method. | Optional and cosmetic per Dortania. It needs `\_SB.PCI0.SBUS` to exist, which is unconfirmed. | **Investigate** ([B-004](backlog.md)). Not in the Monterey baseline. |
| `SSDT-INTELPM.dsl` | Generated by `ssdtPRGen.sh` v21.5 (Piker-Alpha, abandoned) on 10.15.3. Injects `APSS`/`ACST` P-/C-state tables under `\_PR.CPU0–7`, stub `\_SB.LPS0` and `\_GPE.LXEN`, plus `_DSM` `plugin-type`. Paired with CPUFriend. Commits [`23f240c`](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore/commit/23f240ca59ca3b7d515c1762a511cb1f2ef4e135), [`e93f2af`](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore/commit/e93f2af7fbbd433477ef7f886bf04aa0b80ed7ce). | ssdtPRGen tables target the legacy ACPI_SMC_PlatformPlugin. Skylake uses XCPM/`X86PlatformPlugin`, where Dortania recommends only `SSDT-PLUG` (and notes that macOS 12.3+ no longer needs `plugin-type` on Haswell and newer). | **Replace** with OpenCore's precompiled `SSDT-PLUG.aml` (harmless on 12.3+, needed for earlier 12.x installers). Drop the P-/C-state tables, `LPS0`/`LXEN` stubs and CPUFriend unless power measurements show a need ([B-020](backlog.md)). |
| `SSDT-UIAC.dsl` | RehabMan's USBInjectAll port data for xHCI `8086:a12f`: HS01–HS04 and SS01–SS04 as USB3 Type-A (`UsbConnector` 3), HS09 as internal (255). `port-count` 0x1A. | USBInjectAll is unmaintained and relies on injection; current guidance is a codeless or USBToolBox map built on the actual machine. | **Replace** with a generated codeless `USBMap.kext` built from [`hardware/usb/nuc6i7kyb.toml`](../../hardware/usb/nuc6i7kyb.toml). That file reuses the upstream port list as a **provisional, unverified** map, to be replaced by a USBToolBox capture from Windows ([B-010](backlog.md)). |
| Earlier tables removed upstream: `SSDT-NUC6-SC`, `SSDT-HPET`, `SSDT-FixStateTransition`, `SSDT-USB-FixShutdown`, plus `_OSI→XOSI` and `_WAK→XWAK` DSDT patches | Removed upstream in [`2243807`](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore/commit/224380723e89230944ddd52e8a18f1fb2f9e6b4d) after the `XOSI` patch crashed **Windows** booted through OpenCore | Global `_OSI` renames are discouraged; OpenCore applies ACPI changes to every OS it boots | **Remove**. No DSDT binary patches in the baseline. This is direct evidence for the policy in [windows-linux.md](../windows-linux.md): boot Windows/Linux from the firmware menu, not through OpenCore. |
| `ACPI/Quirks` (all false) | Defaults | Same defaults in 1.0.8 | **Retain** the defaults. |

## 3. Booter quirks

| Quirk | Upstream | 1.0.8 Sample / Dortania Skylake | Decision |
| --- | --- | --- | --- |
| `AvoidRuntimeDefrag`, `EnableSafeModeSlide`, `ProvideCustomSlide`, `SetupVirtualMap`, `EnableWriteUnprotector` | true | true | **Retain** |
| `SyncRuntimePermissions` | true | false (Dortania Skylake) | **Investigate** ([B-005](backlog.md)). Default false. The right value depends on whether the firmware exposes a Memory Attributes Table; OpenCore's DEBUG log prints `MAT support is N`. |
| `DisableSingleUser` | true | false | **Remove**: single-user mode is a recovery path. |
| `ProtectUefiServices`, `RebuildAppleMemoryMap`, `DevirtualiseMmio` | false | false | **Retain** false. Revisit only with debug-log evidence. |

## 4. DeviceProperties

| Path / property | Upstream value and history | Current status | Decision |
| --- | --- | --- | --- |
| `Pci(0x2,0x0)` `AAPL,ig-platform-id` | `05003B19` (0x193B0005) | WhateverGreen lists `0x193B0005` as an Iris Pro 580 framebuffer (4 connectors: LVDS + 3 DP, 34 MB stolen). Dortania's laptop/NUC Skylake table lists `05003B19` as "NUC — recommended for HD 580". | **Retain as candidate**. Not yet verified on Monterey. |
| `Pci(0x2,0x0)` `device-id` | `27190000` (0x1927, Iris 550). History: `0x1912` (HD 530) → `0x1927` ([`e174188`](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore/commit/e17418849b7ca78291cd2f9e70182a5e7093e475)) → `0x1912` ([`a182e79`](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore/commit/a182e791d6cc0b7d306c95f4f57cf5cd0fba059e)) → `0x1927` ([`50a6520`](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore/commit/50a6520f674e176de4914b844cdac25c2c8919b7), "Fix occasional Metal application crash … unknown MTLDevice"). **Note:** the upstream README still says "spoofed to Intel HD 530", which is stale. | `0x193B` (the real Iris Pro 580 ID) is natively supported per the WhateverGreen manual, but upstream never shipped a native-ID config, and the only recorded reason for spoofing is a Metal crash. | **Retain as candidate**: `0x1927` is the last configuration upstream reported as working. Native `0x193B` and `0x1912` are A/B variants in [graphics.md](graphics.md) ([B-012](backlog.md)). |
| `enable-hdmi20` | `01000000` | WhateverGreen README: "Not implemented for macOS 11+" | **Remove**. It does nothing on Monterey. HDMI 2.0 on this board goes through a Parade PS175 LSPCON, which the WhateverGreen manual names specifically for the Skull Canyon. |
| LSPCON (`enable-lspcon-support`, `framebuffer-con1-has-lspcon`, `-igfxlspcon`) | Enabled, then removed in [`a182e79`](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore/commit/a182e791d6cc0b7d306c95f4f57cf5cd0fba059e): "Dual monitors appear to work without LSPCON … sleep almost works" | Supported by WhateverGreen 1.3.0+ | **Investigate** ([B-013](backlog.md)): HDMI 2.0 4K60 needs testing with and without LSPCON. Not in the baseline. |
| Connector patches (`framebuffer-conN-pipe` 0x12, `con1-type` HDMI) | Added in `e174188`, rolled back in `c52e7d1`/`a182e79` | — | **Remove**. Upstream had already withdrawn them. |
| `disable-agdc` | `01000000` | Valid WhateverGreen property (`igfxagdc=0`) | **Retain as candidate** (part of upstream's last working state). |
| `force-online` | `01000000`, added in [`10d4193`](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore/commit/10d4193aac2be30499e42d9105629d1982f3fc8b) | Valid WhateverGreen property (`igfxonln=1`) | **Retain as candidate**. It is a plausible lever for the wake black-screen ([B-030](backlog.md)). |
| `enable-metal` | `01000000`. Upstream rationale: "Iris Pro 580 is not a standard GPU used in Macs" | WhateverGreen: "Force enable Metal support on Intel for offline rendering". It is meant for headless iGPUs, which this is not. | **Remove** from the baseline; kept as an A/B variant in [graphics.md](graphics.md). |
| `AAPL,GfxYTile` | Present before `a182e79` | WhateverGreen recommends it for Skylake→Kaby Lake spoofs on macOS 13+ | **Investigate** for Ventura+ only ([B-040](backlog.md)). |
| `Pci(0x1F,0x3)` `alc-layout-id` `20000000` (32) **and** `layout-id` `04000000` (4), `hda-gfx` `onboard-1` | Added in [`ed0dec0`](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore/commit/ed0dec0022d04b74fc6e6ff6dcaaa3da378bb5bd) "Fix sound with AppleALC" | AppleALC 1.9.8 ALC233 still defines layout 32 (MacPeet, written for an ASUS VivoBook S301LA, so not NUC-specific). Dortania recommends a single `layout-id` (or `alcid=`). Recent WhateverGreen sets `hda-gfx` automatically. | **Replace** with a single `layout-id` = 32 as the candidate. Drop the conflicting `layout-id` 4 and the manual `hda-gfx`. Codec identity and layout must be verified ([B-050](backlog.md)). |
| `Pci(0x1b,0x0)` `layout-id` `01000000` | Left over from the OpenCore Sample template; `0x1b` is a PCIe root port on this platform, not HDA | — | **Remove**. |
| ~13 cosmetic `AAPL,slot-name`/`model`/`device_type` entries from Hackintool ([`9c756e7`](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore/commit/9c756e7c788f499fad02ee5a856c266a322e2115)) | Cosmetic. They embed a specific NVMe model (`SM961/PM961`) and slot topology. | No functional effect | **Remove**. They are machine-specific, unverifiable and add noise. |

## 5. Kernel

### Kexts (upstream load order)

| # | Kext | Upstream source | Today | Decision |
| --- | --- | --- | --- | --- |
| 1 | Lilu | Built from source by corpnewt/Lilu-and-Friends | acidanthera release 1.7.2 | **Retain** (official release) |
| 2 | WhateverGreen | Lilu-and-Friends | 1.7.1 | **Retain** |
| 3 | VirtualSMC | Lilu-and-Friends | 1.3.8 (+ `SMCProcessor`) | **Retain**. `SMCSuperIO` is not added until the Super I/O chip is identified ([B-021](backlog.md)). |
| 4 | CPUFriend | Lilu-and-Friends; data provider generated with an unknown tool, never committed | 1.3.0 | **Remove** pending evidence ([B-020](backlog.md)). Without its data-provider kext it does nothing. |
| 5 | NVMeFix | Lilu-and-Friends | 1.1.3 | **Optional**, off by default (`--set nvmefix=true`). Known to misbehave with some drives; enable only when measured ([B-022](backlog.md)). |
| 6 | AppleALC | Lilu-and-Friends | 1.9.8 | **Retain** |
| 7 | IntelMausiEthernet | Mieze GitHub "latest release" | Superseded by acidanthera **IntelMausi** 1.0.8 | **Replace** |
| 8 | USBInjectAll | RehabMan "latest release" | Unmaintained since 2018 | **Replace** with a generated codeless `USBMap.kext` |
| 9 | IntelBluetoothFirmware | zxystd "latest release" | OpenIntelWireless v2.4.0. On macOS 12+, `IntelBluetoothInjector` must not be used; `BlueToolFixup` (acidanthera BrcmPatchRAM 2.7.2) and `IntelBTPatcher` are needed instead. | **Replace** with the modern trio. Optional (`bluetooth` feature, on by default). |
| 10 | AirportItlwm (disabled) | `1hbb/OpenIntelWireless-Factory` (third-party rebuild) | OpenIntelWireless itlwm v2.3.0 ships per-macOS builds (Monterey/Ventura/Sonoma 14.0/14.4) and a generic `itlwm` | **Replace**: official per-OS builds only. `wifi=none` by default; `airportitlwm` and `itlwm` are mutually exclusive and enforced by the validator. |

Upstream left all `MinKernel`/`MaxKernel` empty. Skullintosh sets them per profile so a kext can't
leak into a macOS version it wasn't built for (this matters most for AirportItlwm).

### Kernel quirks

| Quirk | Upstream | Decision |
| --- | --- | --- |
| `AppleCpuPmCfgLock` | true | **Remove**. It is for the legacy `AppleIntelCPUPowerManagement`; Skylake uses XCPM. |
| `AppleXcpmCfgLock` | true | **Retain** until `ControlMsrE2` shows MSR 0xE2 is unlocked ([B-006](backlog.md)). The NUC6 BIOS is not known to expose CFG Lock. |
| `DisableIoMapper` | true | **Retain**. It also means VT-d can stay **enabled** in the BIOS for Windows/Linux (a dual-boot safety improvement over upstream's "disable VT-d" advice). |
| `PanicNoKextDump` | true | **Retain** |
| `PowerTimeoutKernelPanic` | false | **Enable** (Dortania default). It prevents a panic on audio/device power changes. |
| `XhciPortLimit` | false (re-disabled in [`ce67975`](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore/commit/ce67975b6515251463d7d0be833a3ab893975c14)) | **Retain** false. It is broken on macOS 11.3+; a USB map is required instead. |

## 6. Misc / NVRAM / PlatformInfo / UEFI

| Setting | Upstream | Decision and reason |
| --- | --- | --- |
| `Misc/Security/SecureBootModel` | `Disabled` ([`b16d857`](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore/commit/b16d8579a6504e1766a1c1320df4bb88f959a9e4)) | **Replace** with `Default` (Dortania). Apple Secure Boot works with OpenCore-injected kexts. The setting is recorded explicitly so it can't be silently relaxed. |
| `Misc/Security/Vault` | `Optional` | **Retain** `Optional` (the 1.0.8 Sample uses `Secure`, which needs signed vault files). Vaulting is tracked in [B-061](backlog.md). |
| `Misc/Security/ScanPolicy` | 0 (scan everything) | **Replace** with `769` (`0x301`: filesystem lock, APFS + HFS+ only). The OpenCore picker then shows only macOS volumes, so Windows and Linux can't accidentally be booted through OpenCore's ACPI/SMBIOS injection. Use the firmware boot menu (F10) for them. |
| `Misc/Boot/PollAppleHotKeys` | true | **Remove** (default false); revisit if wanted. |
| `Misc/Debug/Target` | 19 | Release builds use the Sample default (3); debug builds use 67 (file logging). |
| `NVRAM boot-args` | `forceRenderStandby=0` ([`2aa2c14`](https://github.com/alexpotter1/intel-nuc6i7kyk-opencore/commit/2aa2c14f25cbc52ddd71f66dbba8f1187f813ecc): iGPU RC6 transitions causing NVMe panics) | **Retain**. The WhateverGreen manual documents exactly this workaround for NVMe panics on iGPU systems. Re-test without it later ([B-031](backlog.md)). |
| `NVRAM UIScale` | `01` | **Remove**; use the default. |
| `PlatformInfo` | `iMac17,1`, null serials, `Automatic` | **Retain** `iMac17,1` for Monterey (Dortania lists it as the Skylake "NUC Systems" SMBIOS). Serials are never committed: placeholders are built in, and a personal identity is applied only at build time from a git-ignored file. |
| `UEFI/Quirks/ReleaseUsbOwnership` | true | **Investigate** ([B-017](backlog.md)). Default false. |
| `UEFI/Quirks/RequestBootVarRouting` | true | **Retain**. It keeps macOS from rewriting the firmware `BootOrder`/`BootNext`, which protects Windows Boot Manager and GRUB. |
| `UEFI/ProtocolOverrides` `AppleRtcRam`, `AppleSmcIo`, `FirmwareVolume`, `HashServices` | true | **Remove** (1.0.8 defaults, with `FirmwareVolume` true). `AppleSmcIo` isn't needed for VirtualSMC; the others belong to FileVault on old firmware. Re-test if FileVault fails ([B-062](backlog.md)). |
| `Misc/Entries` (`CustomOS`, disabled), `Misc/Tools` (Shell/memcheck, disabled) | Disabled placeholders | **Remove** |

## 7. Scripts

| Script | What it did | Problems | Decision |
| --- | --- | --- | --- |
| `setup.sh` | macOS-only orchestrator: clones GenSMBIOS **into the repo** and writes the SMBIOS straight into the tracked `EFI/OC/config.plist` | Encourages committing personal serials; macOS-only; no checksums | **Replace** with `skullintosh build --smbios local/smbios.toml` (the `local/` folder is git-ignored and builds that use it can't be packaged). GenSMBIOS is still the recommended generator, run outside the repo. |
| `get-kexts.sh` | Runs `xcode-select --install`; downloads jq 1.6 (x86-64 only) from an HTTP redirect; builds Lilu plugins from source via corpnewt/Lilu-and-Friends; takes "assets[0] of the latest release" from the GitHub API; edits `config.plist` by array index (`Kernel:Add:9`) with PlistBuddy; `rm -rf` in relative paths | Not reproducible ("latest"), unchecksummed, architecture-specific, fragile index-based edits, a third-party Wi-Fi rebuild | **Replace** with `skullintosh fetch`: pinned versions, SHA-256 verified, official release assets only, cross-platform Python. |
| `build_acpi.sh` | Downloads RehabMan `iasl61.zip` from Bitbucket and compiles every `.dsl` | Dead/unmaintained URL; 2016 compiler | **Replace** with precompiled AML from the pinned OpenCore release. Custom SSDTs (if ever needed) will pin an `iasl` version ([B-003](backlog.md)). |
| `export.sh` | Runs as root: prompts for a disk ID and `mount`+`rsync`s the EFI onto it | Writes to an ESP chosen by free text; no confirmation of what the disk is | **Remove**. Skullintosh never writes to an ESP. [installation.md](../installation.md) documents a manual, verified copy to a removable USB stick. |
| `kexts.txt` | Kext list with a "build from source" flag | — | **Replace** with `profiles/*/profile.toml` + `manifests/dependencies.toml`. |

## 8. Known issues inherited from upstream (README "What doesn't work")

| Issue | Upstream notes | Tracking |
| --- | --- | --- |
| Sleep: sleeps, wakes to a black screen; replugging the display recovers it | Partly improved by removing LSPCON (`a182e79`) | [B-030](backlog.md) |
| Thunderbolt 3 works only when connected at boot; no hot-plug, lost after sleep | Author suggested Hades Canyon-style patches (a different controller and board, so not applicable without verification) | [B-070](backlog.md) |
| SD card reader (PCIe) "unlikely to ever work" | Controller never identified | [B-080](backlog.md) |
| TOSLINK optical "disabled in SSDT" | No such SSDT is in the archived tree | [B-051](backlog.md) |
| ACPI patches apply to Windows/Linux when booted through OpenCore | `XOSI` crashed Windows (`2243807`) | Mitigated by `ScanPolicy` + firmware boot selection ([windows-linux.md](../windows-linux.md)) |
| Secure Boot | Not attempted | [B-061](backlog.md) |

## 9. Other references consulted

* **zearp/Nucintosh** (NUC8 Bean Canyon, actively maintained). Used **only** as a reference for
  current kext choices: BlueToolFixup + IntelBTPatcher for Intel Bluetooth, per-OS AirportItlwm,
  `iMac19,1` for Sonoma/Sequoia, and the Thunderbolt "Legacy security mode" note. Its USB map, ACPI
  and framebuffer data are for a different board and are **not** reused. It ships Lilu 1.7.3 and
  AirportItlwm 2.4.0, which are newer than any official release, so they are presumably nightlies.
  Skullintosh pins official releases only.
* **OpenCore Legacy Patcher**: relevant only to Tahoe/Skylake graphics research; see
  [compatibility.md](../compatibility.md).

## Exit condition

Every inherited component above has a decision with a source. Items marked **Investigate** are
listed in [backlog.md](backlog.md) with a hardware test that would settle them.

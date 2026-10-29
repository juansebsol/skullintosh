# Troubleshooting

Start with the **debug** flavour: it boots verbosely (`-v`) and writes an OpenCore log
(`opencore-*.txt`) to the root of the USB stick's EFI partition. Review logs before sharing
them; they can contain device paths and partition GUIDs.

## Before blaming the EFI

1. `skullintosh validate --target monterey --flavor debug` reports 0 errors.
2. The EFI on the stick is the one you built: compare a file hash with
   `build/…/provenance.json`, or re-copy it.
3. BIOS settings match [bios-settings.md](bios-settings.md), especially Secure Boot **off** and
   DVMT pre-alloc **64 MB**.

## OpenCore stage

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| Stick not in the F10 menu | Fast Boot on; stick not GPT/FAT32; EFI not at the partition root | Disable Fast Boot; check `EFI/BOOT/BOOTx64.efi` exists on the stick's EFI partition |
| Stick listed twice in the F10 menu | The NUC offers a legacy (`USB : …`) and a UEFI (`UEFI : USB : …`) entry for the same stick | Pick the `UEFI :` one; the legacy entry can't start OpenCore |
| `OC: Grabbed zero system-id for SB, this is not allowed` then `Halting on critical error` | Apple Secure Boot (`SecureBootModel` Default) needs a non-zero `system-id`. Builds before this fix shipped the all-zero placeholder UUID. | Rebuild: shared builds now use `SystemUUID` `OEM` (the NUC's own firmware UUID). If the firmware UUID itself is zero, build with `--smbios` and a generated UUID. |
| "Secure Boot Violation" | Firmware Secure Boot enabled | Disable it ([bios-settings.md](bios-settings.md)) |
| Black screen right after choosing the stick | GOP/console issue | Debug log: look for `OCC:` / `GOP` lines; try `UEFI/Output/ProvideConsoleGop` changes ([B-016](backlog.md#b-016)) |
| Picker shows no macOS installer | `ScanPolicy` 769 shows APFS and HFS+ volumes only. A FAT32 `macrecovery` stick sits on a "Msft Basic Data" partition, which is hidden. | Rebuild with `--set fat32_installer=true` (`ScanPolicy` 2817) for the installation, then rebuild without it. Check `com.apple.recovery.boot` is at the stick's root. |
| Keyboard dead in the picker | Firmware USB init | Try another port; keep "Legacy USB Support" on; [B-016](backlog.md#b-016) |
| `OCB: StartImage failed - Aborted` / boot.efi errors | Booter quirk mismatch | Collect the debug log. Check `OCABC: MAT support is …` ([B-005](backlog.md#b-005)) |

## Installer restarts

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| Blue Windows **Recovery** screen after an installer restart: `\Windows\system32\winload.efi`, error `0xc0000225` | The firmware booted its default entry, the Windows Boot Manager on the target disk's old ESP, and Windows is no longer behind it (the volume was erased, the ESP was not). Not a macOS failure. | Press F10, pick the stick, choose `macOS Installer`. Repeat at every restart until the install is done. Erasing the whole *device* in Disk Utility avoids it; a macOS-only disk gets OpenCore on its ESP afterwards ([installation.md](installation.md#if-macos-is-the-only-os-on-the-machines-only-disk)) |
| Install seems to loop: Apple logo and progress bar, a screen of white shutdown text, back to the picker | Normal. Each installer phase ends by shutting down (`unmounting volume macOS Base System`) and restarting, and the debug flavour prints it. | Keep choosing `macOS Installer`. When the picker shows the volume name instead (`Macintosh HD`), the install is finished; choose that. |
| Picker still shows `Install macOS Monterey (external)` after the install | Expected: it is the stick, which is still plugged in | Ignore it. Choosing it starts the install over. |

## Kernel stage (verbose text)

| Last lines | Likely cause | What to do |
| --- | --- | --- |
| Stops at `[EB|#LOG:EXITBS:START]` | Booter quirks / memory map | Debug log + photo; [B-005](backlog.md#b-005) |
| Panic mentioning `AppleIntelCPUPowerManagement` or MSR 0xE2 | CFG Lock | `AppleXcpmCfgLock` must stay on; run ControlMsrE2 (read-only) ([B-006](backlog.md#b-006)) |
| Hang after `IOConsoleUsers: … gIOScreenLockState 3` / garbled screen | iGPU framebuffer | Try the graphics variants ([graphics.md](graphics.md)); check DVMT 64 MB; temporarily add `-igfxvesa` to boot without acceleration and confirm the rest works |
| `Still waiting for root device` | USB map / installer media | Try another port (rear USB 3); the provisional USB map may be wrong ([usb-mapping.md](usb-mapping.md)) |
| Panic with `AppleACPIPlatform` / EC | ACPI path mismatch (`LPCB`) | Collect ACPI tables ([hardware-inventory.md](hardware-inventory.md)); [B-003](backlog.md#b-003) |
| Panic in `IntelBluetoothFirmware` / `itlwm` | Wireless kexts | Rebuild with `--set bluetooth=false --set wifi=none` to isolate |
| NVMe panic during idle | iGPU RC6 | Keep `forceRenderStandby=0` ([B-031](backlog.md#b-031)) |

## In macOS

| Symptom | Check |
| --- | --- |
| "7 MB" VRAM, no Metal | Framebuffer not attached: [graphics.md](graphics.md#verifying-real-acceleration) |
| No sound | `ioreg -l \| grep layout-id`; AppleALC loaded? Try other ALC233 layouts ([B-050](backlog.md#b-050)) |
| No Ethernet | `kextstat \| grep Mausi`; record the I219 PCI ID |
| Wi-Fi greyed out in the Setup Assistant / no Wi-Fi menu | Expected with the default build (`wifi = none`). Rebuild with `--set wifi=airportitlwm` and replace the EFI ([B-092](backlog.md#b-092)) |
| Two volumes called EFI, or `/Volumes/EFI` is the stick | An ESP that Windows formatted is labelled `SYSTEM` and mounts at `/Volumes/SYSTEM`; the stick's is `EFI`. Read `diskutil mount`'s message before copying anything |
| USB 3 devices run at USB 2 speed | Map: SS ports missing ([usb-mapping.md](usb-mapping.md)) |
| Black screen on wake | Known upstream issue ([B-030](backlog.md#b-030)); try waking by keyboard, then replugging the display |
| iCloud/iMessage refuses | SMBIOS identity missing or placeholder; build with `--smbios` ([installation.md](installation.md)) |

## Reporting

Open a **Boot failure** issue with: the `provenance.json`, the last screen (photo) or the
OpenCore debug log (reviewed), BIOS version, and `skullintosh report` output.

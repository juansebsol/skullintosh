# Protecting the existing Windows and Linux installations

The reference machine already dual-boots Windows and Linux from its two internal M.2 SSDs.
Skullintosh development must leave both **independently bootable** at all times.

## Principles

1. **macOS lives on separate, external storage.** The NUC has two M.2 slots and both are used.
   Don't assume a third internal slot exists.
2. **OpenCore boots from removable media, chosen with F10.** It's never the firmware default,
   never on an internal ESP, and never registered in the firmware boot order.
3. **Windows and Linux are booted by the firmware, never through OpenCore.** OpenCore applies
   ACPI tables, device properties and SMBIOS to whatever it boots. Upstream saw Windows crash
   when booted through OpenCore with an `_OSI` patch
   ([audit](upstream-audit.md#2-acpi)).
4. **Nothing is automatic.** No Skullintosh command writes to an ESP, edits partitions, or
   changes UEFI boot entries. The scripts under `scripts/` only read.
5. **Back up first, verify after.** Every test session ends by booting Windows and Linux.

## How the configuration enforces this

| Setting | Value | Effect | Enforced by |
| --- | --- | --- | --- |
| `Misc/Boot/LauncherOption` | `Disabled` | OpenCore never creates or reorders firmware boot entries | validator (`boot-order`) |
| `UEFI/Quirks/RequestBootVarRouting` | `true` | macOS's startup-disk changes go to OpenCore-private variables, not the firmware `BootOrder`/`BootNext` | validator (`boot-order`) |
| `Misc/Security/AllowSetDefault` | `false` | Ctrl+Enter in the picker can't change the default entry | validator (warning) |
| `Misc/Security/ScanPolicy` | `769` (`0x301`) | Picker shows only APFS and HFS+ volumes: Windows (NTFS/ESP) and Linux (ext4/ESP) aren't offered, so they can't be booted with macOS changes applied. `--set fat32_installer=true` (installation only) adds FAT32 data volumes (2817); EFI System Partitions stay hidden. | validator (`scan-policy`) |
| `ResetNvramEntry.efi` arguments | `--preserve-boot` | "Reset NVRAM" in the picker keeps the firmware's Windows Boot Manager and GRUB entries. Without it, OpenCore's NVRAM reset deletes them. | validator (`nvram-reset`) |
| Custom ACPI tables | `SSDT-PLUG`, `SSDT-EC-USBX` only, both gated on `_OSI("Darwin")` | No effect on other OSes even if they were booted through OpenCore | review |
| No DSDT binary patches | — | Upstream's `XOSI` rename broke Windows | review |
| `Kernel/Quirks/DisableIoMapper` | `true` | VT-d can stay enabled in the BIOS for Windows/Linux | — |

## Before each test session

- [ ] Backups from [installation.md](installation.md#1-back-up-the-current-boot-environment)
      exist on media that is **not** inside the NUC.
- [ ] The F10 menu lists Windows Boot Manager and the Linux entry. Note their names.
- [ ] Only stick A (and external disk B) carry OpenCore.

## After each test session

- [ ] Remove stick A. Power on with no F10: the normal default OS boots.
- [ ] Boot the other OS via F10. Both reach the desktop/login.
- [ ] Linux: `sudo efibootmgr -v` matches the backup (`diff` it against `efibootmgr-v.txt`).
- [ ] Windows (elevated): `bcdedit /enum firmware` matches the backup.
- [ ] Record the result in the test report.

If anything differs, stop testing and follow [recovery.md](recovery.md).

## If you later want OpenCore to boot everything

Routing Windows and Linux through OpenCore (`ScanPolicy` 0, OpenLinuxBoot, OpenCore as the
default entry) is **not supported** by Skullintosh. It means the macOS ACPI/SMBIOS changes apply
to the other OSes, and it puts OpenCore in the critical boot path. Any such change needs an
explicit decision from the machine's owner, a backup, and a profile override that the validator
will flag.

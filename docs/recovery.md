# Recovery: restoring the original boot environment

Work from the least invasive step to the most invasive, and stop as soon as things work. Each
step assumes you made the backups in
[installation.md](installation.md#1-back-up-the-current-boot-environment).

## Level 0: remove the USB stick

OpenCore lives only on stick A (and possibly external disk B). Unplug both and power on.
The firmware boots its own default entry exactly as before.

This level doesn't exist on a macOS-only machine where OpenCore was copied to the internal ESP
([installation.md](installation.md#if-macos-is-the-only-os-on-the-machines-only-disk)). There the
stick *is* the recovery path: boot it from F10 and choose the macOS volume, then fix the ESP.

## Level 1: use the firmware boot menu

Press **F10** at power-on and pick **Windows Boot Manager** or the Linux entry (`ubuntu`,
`fedora`, …). If that works, the entries exist and only the default changed: press **F2** →
Boot → Boot Priority and move the right entry back to the top.

## Level 2: BIOS settings

F2 → **Load Defaults**, then re-apply the settings Windows/Linux needed (from your photos), in
particular Secure Boot if it was on. See [bios-settings.md](bios-settings.md#rolling-back).
BitLocker may ask for its recovery key once.

## Level 3: a firmware boot entry is missing

Firmware boot entries can disappear after a "Reset NVRAM" without `--preserve-boot`, a BIOS
reset, or another tool. Skullintosh's validator requires `--preserve-boot`, but recover like this
if it happens anyway.

**Linux entry missing** (boot a Linux live USB from F10):

```bash
sudo efibootmgr -v                            # what exists now
cat /path/to/backup/efibootmgr-v.txt          # what existed before
lsblk -o NAME,SIZE,PARTTYPE,PARTLABEL,MOUNTPOINT
# Recreate the entry pointing at the ESP on the Linux disk; check the path in your backup.
# Example only. Disk, partition number and loader path come from YOUR backup:
sudo efibootmgr --create --disk /dev/nvme1n1 --part 1 --label "ubuntu" \
  --loader '\EFI\ubuntu\shimx64.efi'
```

Alternatively chroot into the installation and reinstall the bootloader
(`grub-install` / `bootctl install`) as your distribution documents.

**Windows Boot Manager missing** (boot the Windows installer USB → Repair → Command Prompt):

```bat
diskpart
  list vol            & rem find the FAT32 ESP on the Windows disk (~100-300 MB)
  sel vol <n>
  assign letter=S
  exit
bcdboot C:\Windows /s S: /f UEFI
```

`bcdboot` recreates the Windows Boot Manager files and firmware entry. Confirm `C:` really is
the Windows volume first (`dir C:\Windows`).

## Level 4: restore an ESP's contents

Only if files on an internal ESP were changed or lost.

* **Linux backup** (`esp-_boot_efi.tar.gz`): from a live USB, mount the Linux ESP (check with
  `lsblk` that it's the right partition), then `sudo tar -C /mnt/esp -xzf esp-_boot_efi.tar.gz`.
  Verify against `SHA256SUMS`.
* **Windows backup** (`ESP\` folder from `-CopyEsp`): from WinRE, mount the ESP as above and
  `robocopy E:\efi-backup-win\ESP S:\ /E`. Then `bcdedit /import E:\efi-backup-win\BCD-backup`
  restores the BCD store, though `bcdboot` (Level 3) is usually enough.

## Level 5: partition tables

Only needed if partitions themselves were damaged, which Skullintosh never does. Linux backups
include `partition-table-<disk>.sfdisk`. Restoring one (`sfdisk /dev/X < file`) overwrites the
partition table, so get help first and image the disk before trying.

## Getting help

Open a **Boot failure** issue with: what you did, which recovery level you reached, and
sanitized output (`skullintosh report --input …`). Don't post serials, MAC addresses, product
keys or BitLocker keys.

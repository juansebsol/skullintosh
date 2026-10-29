# Installation (Monterey baseline)

> [!WARNING]
> The Monterey profile is **unverified on hardware**. Follow this procedure only on a machine
> whose data is backed up, and only on storage you have explicitly chosen for macOS. Read
> [windows-linux.md](windows-linux.md) and [recovery.md](recovery.md) first.

The procedure is built so that, at every step, removing the USB stick returns the NUC to its
original Windows/Linux behaviour.

## 0. What you need

* The NUC6i7KYK with its existing Windows and Linux SSDs, which **stay untouched**.
* **USB stick A** (≥ 16 GB) for the macOS installer and the OpenCore EFI.
* **Target disk B**: an external SSD (USB 3 or Thunderbolt). The NUC has two M.2 slots and both
  are taken, so there is no third internal slot. Don't plan around one.
* A wired Ethernet connection. The default build carries **no Wi-Fi kext** (`wifi = none`), so
  the Setup Assistant greys out "Wi-Fi network". Build with `--set wifi=airportitlwm` before
  making the stick if you need Wi-Fi from the start ([B-092](backlog.md#b-092)).
* Python 3.11+ on any computer, for building.
* Optional: a Mac or macOS VM to make an offline installer.

## 1. Back up the current boot environment

Do this **before** changing BIOS settings or booting anything:

* From Linux: `sudo scripts/backup/linux-backup-boot.sh /path/on/usb/efi-backup-linux`
* From Windows (elevated): `scripts\backup\windows-backup-boot.ps1 -OutputDir E:\efi-backup-win`
* Write down or photograph every BIOS screen you'll change ([bios-settings.md](bios-settings.md)).
* If Windows uses **BitLocker**, make sure you have the recovery key. Changing Secure Boot or
  boot settings can trigger a recovery-key prompt.

## 2. Record the hardware

Run the inventory scripts ([hardware-inventory.md](hardware-inventory.md)) and keep the raw
output private. This confirms the machine really is a NUC6i7KYK with the expected devices.

## 3. Build the EFI

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e .
skullintosh doctor
skullintosh build --target monterey --flavor debug     # first boots: use DEBUG
```

The debug flavour logs to the USB stick (`opencore-*.txt`), boots verbosely, and adds
OpenShell and ControlMsrE2 to the picker (press Space to show them).

This build installs and runs macOS as it is. You need no serial number or other identity for
it; Apple ID, iCloud and iMessage are a separate, optional step after installation
([Optional: Apple ID, iCloud and iMessage](#optional-apple-id-icloud-and-imessage)).

## 4. Make the installer USB (stick A)

**On a Mac (offline installer):**

1. Get `Install macOS Monterey.app`. On older macOS, `softwareupdate` can fetch it:

   ```bash
   softwareupdate --list-full-installers
   softwareupdate --fetch-full-installer --full-installer-version 12.7.6
   ```

   Newer macOS no longer lists Monterey (the reference Mac on macOS 27 printed nothing). Then
   download Apple's own package from Apple's software catalog instead: 12.7.6, build 21H1320,
   **12,409,187,001 bytes**. It needs about 13 GB free on the Mac.

   ```bash
   curl -L -C - -o ~/Downloads/InstallAssistant-12.7.6.pkg "https://swcdn.apple.com/content/downloads/24/16/062-40406-A_LQ4WW26M04/j7bl9ygay5prezturwh72ai10fvseh2uhw/InstallAssistant.pkg"
   stat -f %z ~/Downloads/InstallAssistant-12.7.6.pkg     # must print 12409187001
   pkgutil --check-signature ~/Downloads/InstallAssistant-12.7.6.pkg   # "signed Apple Software"
   sudo installer -pkg ~/Downloads/InstallAssistant-12.7.6.pkg -target /
   ```

   The package only creates the app in `/Applications`; it doesn't upgrade the Mac. If the disk
   fills during the download, the file is silently short and `createinstallmedia` later fails
   with `Couldn't mount dmg … SharedSupport.dmg (error code 113)`. Re-run the same `curl` (`-C -`
   resumes), check the size, then replace the app's copy with it. The package *is* that image:
   `sudo mv ~/Downloads/InstallAssistant-12.7.6.pkg "/Applications/Install macOS Monterey.app/Contents/SharedSupport/SharedSupport.dmg"`.
2. Erase stick A as **GUID Partition Map**, Mac OS Extended (Journaled), named `MyVolume`.
   `createinstallmedia` only erases the *volume* and keeps the partition scheme. A stick that
   was MBR ("FDisk_partition_scheme") ends up with no EFI partition, and there's nowhere to put
   OpenCore. Disk Utility hides the Scheme menu unless **View → Show All Devices** is on, so the
   command line is safer. Check the disk number first:

   ```bash
   diskutil list external physical
   diskutil eraseDisk JHFS+ MyVolume GPT diskN
   ```

   `diskutil list external physical` must then show `GUID_partition_scheme` with an `EFI`
   partition (`diskNs1`).
3. Write the installer (about 30 minutes on a USB 2 stick):

   ```bash
   sudo "/Applications/Install macOS Monterey.app/Contents/Resources/createinstallmedia" --volume /Volumes/MyVolume
   ```

   See also [Apple's guide](https://support.apple.com/en-us/101578).

**On Windows or Linux (online recovery):** use `macrecovery.py`, which ships inside the pinned
OpenCore release (`Utilities/macrecovery/` in the zip cached under `.cache/downloads/opencore/`).
Its `recovery_urls.txt` lists the Monterey command:

```bash
./macrecovery.py -b Mac-E43C1C25D4880AD6 -m 00000000000000000 download
```

Follow Dortania's
[installer guide](https://dortania.github.io/OpenCore-Install-Guide/installer-guide/) to put
`com.apple.recovery.boot` on a FAT32 GUID stick. The installer then downloads macOS over
Ethernet.

A FAT32 stick sits on a "Msft Basic Data" partition, which the default `ScanPolicy` (769) hides.
For the installation session only, build with `--set fat32_installer=true` (`ScanPolicy` 2817:
adds FAT32 data volumes; EFI System Partitions with Windows Boot Manager and GRUB stay hidden).
The validator warns about it. Rebuild without the flag once macOS is installed.

## 5. Copy the EFI onto stick A only

1. Identify stick A beyond doubt: unplug and re-plug it and compare the disk list before and
   after. Check size and model, and that it's marked external/removable.
   * macOS: `diskutil list external physical`, then `sudo diskutil mount diskNs1` for **its**
     EFI partition.
   * Linux: `lsblk -o NAME,SIZE,TRAN,MODEL,PARTTYPE,MOUNTPOINT` (TRAN must be `usb`).
   * Windows: Disk Management (the stick shows as "Removable").
2. Copy the `EFI` folder from `build/monterey-debug[-personal]/` to the root of that partition,
   replacing any `EFI` folder **on the stick only**.
3. Unmount/eject.

Skullintosh never does this step for you, by design.

## 6. BIOS settings

Apply the minimal changes in [bios-settings.md](bios-settings.md). **Don't change the boot
order.**

## 7. First boot

1. Plug in stick A **and** target disk B. Power on and press **F10** for the one-time boot menu.
2. Choose the UEFI entry for stick A. The NUC's F10 menu lists the stick twice: a legacy line
   `USB : <stick name> : PART 0 : OS Bootloader` and a UEFI line `UEFI : USB : <stick name> :
   PART 0 : …`. Take the one that starts with **`UEFI :`**; the legacy line can't start
   OpenCore. Windows and Linux are hidden in the OpenCore picker by design (`ScanPolicy` 769).
3. The picker is a plain text menu titled `OpenCore Boot Menu (DBG-108-…)` with
   `Install macOS Monterey (external)` starred; it boots that entry on its own when the timeout
   runs out. On a `-v` (verbose) boot, note where it stops if it does
   ([troubleshooting.md](troubleshooting.md)). The next screen is macOS Recovery (Restore from
   Time Machine, Install macOS Monterey, Safari, Disk Utility).

## 8. Install onto disk B only

1. In Disk Utility choose **View → Show All Devices**.
2. Identify disk B by model, size and *external* location. The Windows and Linux NVMe drives
   appear as internal disks: **don't select, erase or partition them.**
3. Erase **disk B** (the whole device) as APFS, GUID Partition Map, and install to it.
   Erase the *device*, not just a volume on it. Erasing only the volume keeps the disk's old
   EFI System Partition (and a `Microsoft Reserved` partition) with the Windows boot files in
   it, which is what the firmware then boots after every installer restart (see step 4).
4. The installer restarts three or four times, and each restart needs you, because the firmware
   boots its own default entry, not the stick. On the reference machine that default was the
   leftover Windows Boot Manager, so every restart showed a blue Windows **Recovery** screen
   (`\Windows\system32\winload.efi`, error `0xc0000225`). That screen is not a macOS
   failure. Each time: press F10 at power-on, pick stick A, then in the OpenCore picker:
   * **`macOS Installer`** (starred) while the install is still running. It is the default, so
     letting the timeout expire also works. A phase ends with the Apple logo and a progress
     bar ("About 29 minutes remaining" on the long one), then, on the debug flavour, a screen of
     white shutdown text (`unmounting volume macOS Base System`, launchd services exiting) and a
     restart. That text is the installer shutting itself down, not an error.
   * **The volume name you chose** (for example `Macintosh HD`) once `macOS Installer` has
     disappeared from the picker. That is the finished install; it boots to the Setup
     Assistant.

   Don't pick `Install macOS Monterey (external)` again: it starts the whole install over.

### Setup Assistant

* "Wi-Fi network" is greyed out with the default build (no Wi-Fi kext); choose
  "Local network (Ethernet)" or "does not connect".
* Skip the Apple ID sign-in. The default build uses OpenCore's placeholder serial
  (`W00000000001`, the same on every copy), and Apple services don't work with it. Signing in
  now and changing the serial later can get the account flagged. See
  [Optional: Apple ID, iCloud and iMessage](#optional-apple-id-icloud-and-imessage).
* Decline Location Services, Siri and analytics; they add nothing to the tests.
* The clock shows a stale date (Dec 31) until the first network connection sets it.

## 9. After installation

* Keep booting from stick A for now. Later you can copy the EFI to **disk B's** EFI partition
  (still external) so disk B boots on its own from the F10 menu. Do **not** copy OpenCore to
  an internal ESP, or make it the default boot entry, without an explicit, documented
  decision. The one documented case is below.
* Keep stick A, plus a zipped copy of the working `EFI` folder, as the rescue path.
* Go through the [hardware test checklist](hardware-testing.md) and file a
  **Compatibility test report** with your `provenance.json`.
* Check that Windows and Linux still boot from F10 ([windows-linux.md](windows-linux.md)).

### If macOS is the only OS on the machine's only disk

Only after the machine's owner has decided that no other OS stays on that disk. The reference
machine has been in this state since 2026-10-29: one internal 128 GB NVMe that used to hold
Windows, erased at volume level during the install. Booting through the stick keeps working,
but without it every power-on lands on the leftover Windows Boot Manager. To make the disk boot
on its own:

1. In Terminal, `diskutil list`. Both EFI System Partitions show the type `EFI`, but a partition
   that Windows created is *labelled* `SYSTEM`, so it mounts at `/Volumes/SYSTEM`, while the
   stick's is labelled `EFI` and mounts at `/Volumes/EFI`. Read the mount messages instead of
   assuming which is which.

   ```bash
   sudo diskutil mount disk0s1     # internal -> "Volume SYSTEM on disk0s1 mounted"
   sudo diskutil mount disk2s1     # stick    -> "Volume EFI on disk2s1 mounted"
   ls -R /Volumes/SYSTEM/EFI | head -20   # expect Boot/bootx64.efi and Microsoft/ (Windows)
   ls /Volumes/EFI/EFI                    # expect BOOT and OC (OpenCore)
   ```

2. Replace the Windows boot files with the OpenCore folder from the stick, then compare:

   ```bash
   sudo rm -rf /Volumes/SYSTEM/EFI
   sudo cp -R /Volumes/EFI/EFI /Volumes/SYSTEM/
   diff -rq /Volumes/EFI/EFI /Volumes/SYSTEM/EFI   # only "._*" AppleDouble files may differ
   ```

   The `Microsoft Reserved` partition Disk Utility left behind is harmless and can stay.
3. Shut down, remove the stick, power on. With a single disk no boot-order change is needed:
   the firmware falls back to `EFI/BOOT/BOOTx64.efi` on that disk, which is OpenCore's
   launcher. The picker appears with the macOS volume starred and boots it after the timeout.
   Set the disk first in the BIOS boot order only if you add a second disk later.
4. From now on the stick is the rescue path, and Level 0 of [recovery.md](recovery.md) no
   longer applies to this machine. Restoring Windows would need its installer
   ([recovery.md, Level 3](recovery.md#level-3-a-firmware-boot-entry-is-missing)).

## Switching to the release flavour

When debug boots work, build `--flavor release` (no verbose output or file logging) and replace
the EFI folder on stick A. Keep a copy of the working debug EFI next to it as `EFI-debug-backup`
(it can't boot from that name; it's only a spare).

## Optional: Apple ID, iCloud and iMessage

Skip this unless you want Apple services. Everything above, including installing and using
macOS, works without it.

Every default build carries OpenCore's placeholder identity: serial `W00000000001`, board
serial `M0000000000000001`, and the NUC's own firmware UUID. Apple ID, iCloud, iMessage,
FaceTime and App Store sign-in need an identity of your own, which stays on your machine and
never goes in this repository.

1. Run [GenSMBIOS](https://github.com/corpnewt/GenSMBIOS) **outside** this repository and
   generate an `iMac17,1` identity (the profile's model; other profiles name theirs in
   `profile.toml`).
2. Create `local/smbios.toml` (the `local/` folder is git-ignored):

   ```toml
   SystemSerialNumber = "<serial from GenSMBIOS>"
   MLB = "<board serial from GenSMBIOS>"
   SystemUUID = "<UUID from GenSMBIOS>"
   ROM = "<12 hex digits, e.g. from the NIC MAC address>"
   ```

3. Build with it, adding the same `--set` options as your current build (for example
   `--set wifi=airportitlwm`):

   ```bash
   skullintosh build --target monterey --flavor debug --smbios local/smbios.toml
   ```

   The output goes to `build/monterey-debug-personal/`, carries a
   `PERSONALIZED-DO-NOT-SHARE.txt` marker, and `skullintosh package` refuses it.
4. Replace the `EFI` folder wherever you boot from (stick A, or the disk's own EFI partition)
   the same way as before, reboot, then sign in under System Preferences → Apple ID.

Never paste these values into issues, logs or screenshots. `skullintosh scan-secrets` checks the
working tree. Pick an identity once and keep it: changing the serial after signing in can get
the account flagged.

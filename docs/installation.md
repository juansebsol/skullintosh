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
* A wired Ethernet connection (Wi-Fi is off by default).
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

### Your SMBIOS identity (needed for iCloud/iMessage; optional for first tests)

1. Run [GenSMBIOS](https://github.com/corpnewt/GenSMBIOS) **outside** this repository and
   generate an `iMac17,1` identity.
2. Create `local/smbios.toml` (the `local/` folder is git-ignored):

   ```toml
   SystemSerialNumber = "<serial from GenSMBIOS>"
   MLB = "<board serial from GenSMBIOS>"
   SystemUUID = "<UUID from GenSMBIOS>"
   ROM = "<12 hex digits, e.g. from the NIC MAC address>"
   ```

3. `skullintosh build --target monterey --flavor debug --smbios local/smbios.toml`.
   The output goes to `build/monterey-debug-personal/`, carries a
   `PERSONALIZED-DO-NOT-SHARE.txt` marker, and `skullintosh package` refuses it.

Never paste these values into issues, logs or screenshots. `skullintosh scan-secrets` checks the
working tree.

## 4. Make the installer USB (stick A)

**On a Mac (offline installer):**

```bash
softwareupdate --list-full-installers
softwareupdate --fetch-full-installer --full-installer-version 12.7.6
```

Then use Apple's `createinstallmedia` ([Apple guide](https://support.apple.com/en-us/101578)).
It formats stick A as GUID/HFS+ with an EFI partition.

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
2. Choose the UEFI entry for stick A. Windows and Linux are hidden in the OpenCore picker by
   design (`ScanPolicy` 769).
3. Choose the macOS installer. On a `-v` (verbose) boot, note where it stops if it does
   ([troubleshooting.md](troubleshooting.md)).

## 8. Install onto disk B only

1. In Disk Utility choose **View → Show All Devices**.
2. Identify disk B by model, size and *external* location. The Windows and Linux NVMe drives
   appear as internal disks: **don't select, erase or partition them.**
3. Erase **disk B** (the whole device) as APFS, GUID Partition Map, and install to it.
4. The installer reboots several times. Each time, press F10, pick stick A, then in the
   OpenCore picker pick the "macOS Installer" entry, later the disk-B volume name.

## 9. After installation

* Keep booting from stick A for now. Later you can copy the EFI to **disk B's** EFI partition
  (still external) so disk B boots on its own from the F10 menu. Do **not** copy OpenCore to
  either internal ESP, or make it the default boot entry, without an explicit, documented
  decision.
* Go through the [hardware test checklist](hardware-testing.md) and file a
  **Compatibility test report** with your `provenance.json`.
* Check that Windows and Linux still boot from F10 ([windows-linux.md](windows-linux.md)).

## Switching to the release flavour

When debug boots work, build `--flavor release` (no verbose output or file logging) and replace
the EFI folder on stick A. Keep a copy of the working debug EFI next to it as `EFI-debug-backup`
(it can't boot from that name; it's only a spare).

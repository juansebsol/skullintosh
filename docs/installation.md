# Installation (macOS Monterey)

This guide installs macOS 12 Monterey on a NUC6i7KYK and leaves it booting macOS on its own,
without the USB stick. It is the path that was run end to end on the reference machine on
2026-10-29. Expect about two hours, most of it waiting.

What you end up with: a disk that holds only macOS, with OpenCore on that disk's EFI partition.
OpenCore starts first at every boot, loads the drivers for this hardware, then starts macOS.

> [!IMPORTANT]
> The disk you install to and the USB stick are **erased**. If the NUC has disks you want to
> keep (Windows, Linux), the simplest safe option is to **take them out** before you start and
> put them back afterwards. To keep them installed instead, read
> [windows-linux.md](windows-linux.md) first.

## What you need

* The NUC6i7KYK.
* A disk for macOS, 64 GB or more. It will be erased.
* A USB stick, 16 GB or more. It will be erased.
* A Mac with Python 3.11+, to build the EFI and make the installer stick. (Without a Mac, see
  [Making the stick on Windows or Linux](#making-the-stick-on-windows-or-linux).)
* A **USB keyboard**: wired, or wireless with a USB receiver. A Bluetooth-only keyboard doesn't
  work in the BIOS or the OpenCore menu. A mouse helps in the installer but isn't required.
* Optional: Ethernet. The build below includes Wi-Fi.

## 1. Build the EFI

On the Mac:

```bash
git clone https://github.com/juansebsol/skullintosh && cd skullintosh
python3 -m venv .venv && . .venv/bin/activate
pip install -e .
skullintosh doctor
skullintosh build --target monterey --flavor debug --set wifi=airportitlwm
```

The result is `build/monterey-debug/EFI`. The last line must say `0 error(s)`.

* `--flavor debug` shows boot messages as text, so a failure can be photographed and
  diagnosed. Switch to `release` once everything works ([Next steps](#next-steps)).
* `--set wifi=airportitlwm` adds the Wi-Fi driver ([wifi.md](wifi.md)).
* No serial number is needed. Apple ID, iCloud and iMessage are an optional later step
  ([apple-services.md](apple-services.md)).

## 2. Download macOS Monterey

You need `Install macOS Monterey.app` (12.7.6) in `/Applications`.

On macOS 13 or older, `softwareupdate` can fetch it:

```bash
softwareupdate --fetch-full-installer --full-installer-version 12.7.6
```

Newer macOS doesn't offer Monterey any more. Download Apple's own package from Apple's software
catalog instead. It is 12.4 GB, so make sure about 13 GB is free:

```bash
curl -L -C - -o ~/Downloads/InstallAssistant-12.7.6.pkg "https://swcdn.apple.com/content/downloads/24/16/062-40406-A_LQ4WW26M04/j7bl9ygay5prezturwh72ai10fvseh2uhw/InstallAssistant.pkg"
stat -f %z ~/Downloads/InstallAssistant-12.7.6.pkg                  # must print 12409187001
pkgutil --check-signature ~/Downloads/InstallAssistant-12.7.6.pkg   # must say "signed Apple Software"
sudo installer -pkg ~/Downloads/InstallAssistant-12.7.6.pkg -target /
```

The package only creates the app in `/Applications`; it doesn't change the Mac's own macOS.

If the size is wrong (the disk filled up during the download), run the same `curl` again: `-C -`
resumes it.

## 3. Make the USB stick

1. Find the stick's disk number (`diskN`) by its size:

   ```bash
   diskutil list external physical
   ```

2. Erase it as GUID. Replace `diskN`, and check twice that it's the stick:

   ```bash
   diskutil eraseDisk JHFS+ MyVolume GPT diskN
   ```

   `diskutil list external physical` must now show `GUID_partition_scheme` with an `EFI`
   partition. Without GUID there is no EFI partition and no place for OpenCore.
3. Write the installer to it (about 30 minutes):

   ```bash
   sudo "/Applications/Install macOS Monterey.app/Contents/Resources/createinstallmedia" --volume /Volumes/MyVolume
   ```

4. Copy the EFI onto the stick's EFI partition, then eject:

   ```bash
   sudo diskutil mount diskNs1
   cp -R build/monterey-debug/EFI /Volumes/EFI/ && ls /Volumes/EFI/EFI   # BOOT  OC
   diskutil eject diskN
   ```

## 4. BIOS settings

Press **F2** at power-on. Photograph each screen before changing anything, then set:

| Setting | Value |
| --- | --- |
| Boot → Secure Boot | Disabled |
| Boot → Boot Configuration → Fast Boot | Disabled |
| Devices → Video → IGD Minimum Memory | 64 MB |
| Devices → Video → IGD Aperture Size | 256 MB |

Leave everything else, including the boot order, as it is. Press F10 to save. Details and rolling
back: [bios-settings.md](bios-settings.md).

## 5. Boot the installer

1. Plug the stick into the NUC, power on, and press **F10**.
2. Choose the entry that starts with **`UEFI : USB`**. The plain `USB :` entry is legacy mode
   and can't start OpenCore.
3. The OpenCore menu appears with `Install macOS Monterey (external)` selected and starts it
   after 5 seconds.
4. White text scrolls (debug build). It can pause for several minutes at
   `validate_root_image` on a USB 2 stick. The installer screen (Restore from Time Machine,
   Install macOS Monterey, Safari, Disk Utility) follows.

If it stops, photograph the last screen of text and see
[troubleshooting.md](troubleshooting.md).

## 6. Install macOS

1. Open **Disk Utility** and choose **View → Show All Devices**.
2. Select the target disk itself (the top line of that device, not a volume under it). Check
   the model and size.
3. **Erase** it with Name `Macintosh HD`, Format **APFS**, Scheme **GUID Partition Map**.
   Erase the whole device: erasing only a volume keeps the disk's old EFI partition, and with it
   any old Windows boot files.
4. Quit Disk Utility, choose **Install macOS Monterey**, and pick `Macintosh HD`.

The installer restarts three or four times. **Keep the stick in.** At each restart:

* If the NUC doesn't return to the OpenCore menu by itself, press **F10** and choose
  `UEFI : USB` again. (On a disk that held Windows before, the restart can land on a blue
  Windows recovery screen; that's the old boot files, not a failure.)
* In the OpenCore menu, pick **`macOS Installer`** while it's listed (it's the default), and
  **`Macintosh HD`** once it disappears.
* Don't pick `Install macOS Monterey (external)` again: it starts over.

A screen of white shutdown text before each restart is normal in the debug build.

### Setup Assistant

* Join Wi-Fi, or use Ethernet.
* **Skip the Apple ID sign-in** ([apple-services.md](apple-services.md) explains why).
* The rest is up to you.

## 7. Boot without the stick

So far OpenCore only lives on the stick. Copy it to the disk's own EFI partition. On the NUC, with
the stick still in, open Terminal:

1. Find both disks:

   ```bash
   diskutil list
   ```

   * The **internal disk**: `(internal, physical)`, usually `disk0`. Its EFI partition is
     `disk0s1`.
   * The **stick**: `(external, physical)`, 31 GB or so, with `Install macOS Monterey`. Its EFI
     partition is `diskNs1`.
2. Mount both EFI partitions at fixed folders. Replace `disk0s1` and `diskNs1` with what you
   found:

   ```bash
   mkdir -p /tmp/esp-disk /tmp/esp-stick
   sudo diskutil mount -mountPoint /tmp/esp-disk disk0s1
   sudo diskutil mount -mountPoint /tmp/esp-stick diskNs1
   ```

3. Replace the disk's EFI folder with the stick's:

   ```bash
   sudo rm -rf /tmp/esp-disk/EFI && sudo cp -R /tmp/esp-stick/EFI /tmp/esp-disk/ && ls /tmp/esp-disk/EFI   # BOOT  OC
   ```

4. Shut down, remove the stick, and power on.

The NUC now starts OpenCore from the disk and boots macOS after 5 seconds. No BIOS boot-order
change is needed when it's the only disk. With more than one disk, put this one first in
F2 → Boot → Boot Priority.

**Keep the stick.** It is the rescue path: if the disk ever stops booting, F10 → `UEFI : USB` →
`Macintosh HD` still works.

## 8. Apply the macOS settings

Some fixes live in macOS's own settings, where the EFI can't reach them. On the NUC, download
and run the post-install script:

```bash
curl -fsSLO https://raw.githubusercontent.com/juansebsol/skullintosh/main/scripts/macos/post-install.sh
bash post-install.sh --dry-run   # shows what it will change
sudo bash post-install.sh
```

It turns off hibernation and the related deep-sleep modes, which non-Apple firmware can't wake
from. Without it, the reference NUC went to sleep and never woke up. Undo with
`sudo pmset restoredefaults`.

## 9. Check that it works

Run the core checks in [hardware-testing.md](hardware-testing.md#core-required-for-verified) and
report the results (Compatibility test report issue). Until those pass, the Monterey profile is a
candidate.

## Updating the EFI later

Use this for any new build: a newer Skullintosh, Wi-Fi added, the release flavour, an SMBIOS
identity.

1. **Build** the new EFI on the Mac (`skullintosh build …`).
2. **Put it on the stick:** mount the stick's EFI partition, replace its `EFI` folder, eject
   (as in [step 3.4](#3-make-the-usb-stick), with `rm -rf /Volumes/EFI/EFI` first).
3. **Test from the stick:** on the NUC, F10 → `UEFI : USB` → `Macintosh HD`. The disk isn't
   touched yet; if something is wrong, remove the stick and reboot.
4. **Copy it to the disk** with [step 7](#7-boot-without-the-stick).

## Next steps

* **Release flavour:** `skullintosh build --target monterey --set wifi=airportitlwm`, then
  [update the EFI](#updating-the-efi-later). No boot text, and the menu only lists macOS.
* **Wi-Fi** on a build without it, or on other macOS versions: [wifi.md](wifi.md).
* **Apple ID, iCloud, iMessage:** [apple-services.md](apple-services.md).
* **Something broke:** [troubleshooting.md](troubleshooting.md) and [recovery.md](recovery.md).

## Making the stick on Windows or Linux

Without a Mac, make an online-recovery stick instead. The installer then downloads macOS over
**Ethernet**.

1. Build the EFI with one more option, because the recovery stick is FAT32 and the default
   `ScanPolicy` hides FAT32 volumes:

   ```bash
   skullintosh build --target monterey --flavor debug --set wifi=airportitlwm --set fat32_installer=true
   ```

2. Download the recovery image with `macrecovery.py`, which ships in the OpenCore release
   (`Utilities/macrecovery/` in the zip under `.cache/downloads/opencore/`):

   ```bash
   python3 macrecovery.py -b Mac-E43C1C25D4880AD6 -m 00000000000000000 download
   ```

3. Format the stick as GPT/FAT32 and copy `com.apple.recovery.boot` and the `EFI` folder to its
   root, following Dortania's
   [installer guide](https://dortania.github.io/OpenCore-Install-Guide/installer-guide/).
4. Continue at [step 4](#4-bios-settings). Once macOS is installed, rebuild **without**
   `fat32_installer` before [step 7](#7-boot-without-the-stick).

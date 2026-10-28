# USB mapping

macOS only enumerates 15 ports per xHCI controller, and `XhciPortLimit` doesn't work on
macOS 11.3+. A correct map is therefore required. Skullintosh builds a **codeless**
`USBMap.kext` (an `AppleUSBHostMergeProperties` personality, no executable) from
[hardware/usb/nuc6i7kyb.toml](../hardware/usb/nuc6i7kyb.toml) for every profile, matching the
profile's SMBIOS model.

## Current state: provisional

The data file copies the archived upstream `SSDT-UIAC.dsl` port list: HS01–HS04 + SS01–SS04 as
USB 3 Type-A, and HS09 as internal (presumed Bluetooth). It was made for this exact model, but:

* which physical socket each port belongs to was never recorded,
* the Bluetooth port assignment is unconfirmed,
* it is marked `verified = false`, and the build labels the kext "UNVERIFIED provisional map".

The Thunderbolt 3 USB-C port has its own xHCI controller (Alpine Ridge). It only appears when a
device is connected and is out of scope for this map ([B-070](backlog.md#b-070)).

## Building the real map with USBToolBox (from Windows)

Windows is already installed, which makes USBToolBox the easiest route.

1. Download `Windows.exe` from the official
   [USBToolBox/tool releases](https://github.com/USBToolBox/tool/releases) (v0.2 at the time of
   writing). Check that it really came from that repository.
2. Run it, then choose **Discover Ports**.
3. Using one USB 2 stick and one USB 3 stick, plug each into **every physical port** in turn:
   both front Type-A ports (one is the yellow charging port), both rear Type-A ports, and the
   USB-C/TB3 port. Wait for the tool to register each one.
4. Note in the tool which port numbers lit up for each physical socket, for both the USB 2
   (HSxx) and USB 3 (SSxx) personalities.
5. Note the internal Bluetooth port (it appears with the Intel Bluetooth device attached).
6. **Don't use the tool's kext output directly.** Copy the port numbers and types into
   `hardware/usb/nuc6i7kyb.toml`, filling in `physical = "front left (yellow)"` and so on.
   This keeps the map reproducible and reviewable.
7. Set `verified = true` only after the physical tests below pass. Record the evidence in the
   pull request.

The Windows tool needs no installation, but treat it like any downloaded executable. The
`USBToolBox.kext` + `UTBMap.kext` route is an alternative if the codeless map ever proves
insufficient; it would add a dependency to the manifest.

## Physical test table (T-USB-1)

| Physical port | Connector | HS port | SS port | USB 2 device | USB 3 device (≥ 300 MB/s) | Keyboard in picker | After sleep |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Front, yellow (charging) | Type-A | | | | | | |
| Front, black | Type-A | | | | | | |
| Rear, left | Type-A | | | | | | |
| Rear, right | Type-A | | | | | | |
| Internal Bluetooth | internal | | — | Bluetooth works | — | — | reconnects |

Also check: a USB storage copy of a large file (≥ 4 GB) at expected speed on each SS port, a
keyboard and mouse at the OpenCore picker and FileVault prompt, and that no port shows twice in
System Information → USB.

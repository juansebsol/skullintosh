# BIOS settings (NUC6i7KYK Visual BIOS)

Press **F2** at power-on to enter setup and **F10** for the one-time boot menu. Exact menu
names differ between BIOS versions. Record your version (Main screen) in
[hardware-inventory.md](hardware-inventory.md).

> [!IMPORTANT]
> **Before changing anything:** photograph every screen you'll touch, or note the current
> values in the table below. If Windows uses BitLocker, have the recovery key ready: changing
> Secure Boot can trigger a BitLocker recovery prompt. Don't update or downgrade the BIOS as
> part of Skullintosh work. If you do update for other reasons, re-check every setting below,
> because updates reset them.

## Required for OpenCore

| Setting (typical location) | Set to | Why | Effect on Windows/Linux | Original value |
| --- | --- | --- | --- | --- |
| Boot → Secure Boot | **Disabled** | Skullintosh's OpenCore is not signed for UEFI Secure Boot ([B-061](backlog.md#b-061)) | Windows boots fine; BitLocker may ask for the recovery key once. Linux with shim still boots. | |
| Boot → Boot Configuration → UEFI Boot | **Enabled** | OpenCore is UEFI-only | None (already UEFI on modern installs) | |
| Boot → Boot Configuration → Legacy Boot | Disabled (if present) | Avoid CSM | None for UEFI installs | |
| Boot → Boot Configuration → Fast Boot | **Disabled** | USB devices must be enumerated so the stick and F10 menu work | Slightly slower POST | |
| Devices → Video → IGD Minimum Memory (DVMT pre-allocated) | **64 MB** | Framebuffer `0x193B0005` needs 34 MB stolen; upstream used 64 MB. Without it, use `framebuffer-stolenmem` patches instead. | Negligible | |
| Devices → Video → IGD Aperture Size | **256 MB** | Upstream used 128/256 MB | Negligible | |

## Leave as they are

| Setting | Recommendation | Why |
| --- | --- | --- |
| **Boot priority / boot order** | **Do not change** | Use F10 for each macOS boot. The firmware default stays Windows Boot Manager or GRUB. |
| Intel VT-d | Leave as is (Enabled is fine) | Skullintosh sets `DisableIoMapper`, so upstream's "disable VT-d" advice is no longer needed. Windows (Hyper-V, WSL2, Core Isolation) and Linux (IOMMU) keep working. |
| Intel VT-x | Leave enabled | Harmless to macOS |
| Intel PTT / TPM | Leave as is | BitLocker depends on it |
| Legacy USB Support | Leave enabled | Keyboard in the OpenCore picker |

## Optional, for specific tests only

Only change these while testing that subsystem, and change them back afterwards.

| Setting | Test value | For | Risk to other OSes |
| --- | --- | --- | --- |
| Security → Thunderbolt Security Level | Legacy Mode (no security) | Thunderbolt tests ([B-070](backlog.md#b-070)); the NUC8 project needs this | Windows no longer asks before authorizing Thunderbolt devices |
| Power → Wake on LAN from S4/S5 | Stay Off | Sleep tests ([B-030](backlog.md#b-030)) | Wake-on-LAN stops working |
| Devices → USB → Port Device Charging Mode | Off | Sleep/USB tests | No charging from the yellow port while off |
| Devices → Onboard Devices → Card Reader, Consumer IR, Wi-Fi, Bluetooth | Disabled | Isolating a subsystem | Device disappears from all OSes |

## CFG Lock

The NUC6 BIOS is not known to expose a CFG Lock option, so Skullintosh keeps the
`AppleXcpmCfgLock` quirk enabled. The debug build includes `ControlMsrE2.efi`. Running it
**without arguments** only reports whether MSR 0xE2 is locked. Don't run it with
`unlock`/`lock`, which write firmware variables, unless a maintainer has asked you to and you've
recorded the result ([B-006](backlog.md#b-006)).

## Rolling back

1. F2 → **Load Defaults** (F9 in most versions) restores factory settings. Then re-apply any
   non-default settings Windows/Linux relied on (from your photos), such as Secure Boot
   **Enabled** if it was on before.
2. Turning Secure Boot back on: Boot → Secure Boot → Enabled. If Windows asks for the BitLocker
   key, enter it once; Windows reseals to the TPM afterwards.
3. Boot order: if anything changed it (it shouldn't), set Windows Boot Manager or the Linux
   entry first again. Missing entries: [recovery.md](recovery.md).

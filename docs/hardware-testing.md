# Hardware testing procedures

CI checks that an EFI is well-formed. Only these physical tests can show it **works**. A profile
moves from `candidate` to `verified` only when the core tests below pass on a NUC6i7KYK and are
recorded with the build's tree digest.

## Every test run records

* `provenance.json` from the build (profile, flavour, features, every file hash).
* `skullintosh build` prints `tree digest …`. Quote it.
* macOS version and build (`sw_vers`), BIOS version, BIOS settings changed.
* Pass/fail per test ID below, with notes.
* Confirmation that Windows and Linux still boot ([windows-linux.md](windows-linux.md)).

Use the **Compatibility test report** issue template.

## Core (required for `verified`)

| ID | Test | Pass criteria | How to check |
| --- | --- | --- | --- |
| T-BOOT-1 | Boot installer from USB via F10 | Installer GUI appears | — |
| T-BOOT-2 | Install to the target disk | Completes; every other disk untouched | Disk Utility before/after; the installer restarts several times, see [installation.md](installation.md#6-install-macos) |
| T-BOOT-3 | Cold boot ×5 into installed macOS | 5/5 reach the login window | — |
| T-BOOT-4 | Reboot and shutdown ×5 | No hang, no panic | `log show --last boot --predicate 'eventMessage contains "panic"'` |
| T-GFX-1 | Real graphics acceleration | VRAM ≈ 1536 MB; Metal supported | System Information → Graphics/Displays; `system_profiler SPDisplaysDataType` shows "Metal Support" |
| T-GFX-2 | Framebuffer driver loaded | `AppleIntelSKLGraphicsFramebuffer` (Monterey) | `kextstat \| grep -i intel` or `kmutil showloaded \| grep -i Intel` |
| T-GFX-3 | Metal workload | No crash, plausible FPS | e.g. Geekbench Metal / Unigine Heaven (record score) |
| T-GFX-4 | Video decode | Hardware HEVC/H.264 decode | VideoProc or `VDADecoderChecker`-style tool; Activity Monitor GPU history |
| T-NET-1 | Ethernet | DHCP lease, 1 Gbit/s link, sustained transfer | Network settings; `iperf3` |
| T-USB-1 | USB map | See [usb-mapping.md](dev/usb-mapping.md) test table | — |
| T-AUD-1 | Headphone output | Sound, no distortion | Plug in headphones |
| T-SEC-1 | SIP enabled | `System Integrity Protection status: enabled.` | `csrutil status` |
| T-DUAL-1 | Windows still boots via F10 | Reaches login | — |
| T-DUAL-2 | Linux still boots via F10 | Reaches login | — |
| T-DUAL-3 | Firmware boot entries unchanged | `efibootmgr -v` / `bcdedit /enum firmware` match the backup | `diff` |

## Extended (per subsystem; failures are documented, not blockers)

| ID | Test | How |
| --- | --- | --- |
| T-GFX-5 | HDMI 2.0: 4K60 on a 4K60 HDMI 2.0 display | System Settings → Displays; refresh rate shown |
| T-GFX-6 | Mini DP output | Connect alone and with HDMI |
| T-GFX-7 | USB-C/TB3 DP output | USB-C → DP cable |
| T-GFX-8 | Hot-plug each output ×3 | Unplug and replug while logged in |
| T-GFX-9 | Dual and triple displays | All combinations of HDMI + mDP + USB-C |
| T-AUD-2 | Microphone input (front combo jack) | Voice Memos; input level meter |
| T-AUD-3 | HDMI audio | Choose the HDMI device in Sound output |
| T-AUD-4 | TOSLINK optical | Optical device in Sound output; external DAC |
| T-AUD-5 | Audio after sleep | Repeat T-AUD-1 after T-PWR-2 |
| T-WIFI-1 | Wi-Fi association, 5 GHz, throughput | `iperf3`; AirportItlwm: native menu; itlwm: HeliPort |
| T-WIFI-2 | Wi-Fi after sleep | Reconnects within 30 s |
| T-BT-1 | Bluetooth pairing (keyboard, mouse, headphones) | Bluetooth settings |
| T-BT-2 | Bluetooth reconnect after sleep and reboot | — |
| T-BT-3 | Wi-Fi/Bluetooth coexistence | Stream Bluetooth audio while downloading over Wi-Fi |
| T-PWR-1 | CPU idle and turbo | Intel Power Gadget is gone on recent macOS; use `sudo powermetrics --samplers cpu_power -i 1000 -n 30`. Idle ≈ 0.8 GHz, turbo to 3.5 GHz |
| T-PWR-2 | Sleep/wake ×10 (Apple menu → Sleep; wake by keyboard) | Display returns each time, no panic; `pmset -g log \| grep -E "Sleep\|Wake"` |
| T-PWR-3 | Sleep with USB/Thunderbolt peripherals attached | Peripherals usable after wake |
| T-PWR-4 | Sustained load 30 min | No throttling below base clock; fan behaviour noted; temps from `powermetrics` |
| T-TB-1 | Thunderbolt device present at boot | Device works |
| T-TB-2 | Thunderbolt hot-plug | Device appears without reboot |
| T-TB-3 | Thunderbolt after sleep | Device still works |
| T-SD-1 | SD card insert | Card mounts (expected to fail; record the controller ID) |
| T-NVME-1 | NVMe power | Idle power/temperature with and without NVMeFix |
| T-FV-1 | FileVault | Enable, reboot, unlock at the OpenCore/Apple prompt |

## Comparing configurations

When testing a change (for example the `device-id` variants in [graphics.md](dev/graphics.md)):

1. Build both variants; keep both `provenance.json` files.
2. `diff` the two generated `config.plist` files and paste the diff into the report.
3. Run the same test IDs on both, in the same order, with the same peripherals.
4. Change one thing at a time.

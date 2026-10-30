# Iris Pro Graphics 580

The i7-6770HQ's GT4e iGPU (PCI `8086:193b`, 128 MB eDRAM) drives all three outputs: HDMI 2.0
(through a Parade PS175 LSPCON, which WhateverGreen's manual names specifically for the Skull
Canyon), Mini DisplayPort 1.2, and DisplayPort over the Thunderbolt 3 USB-C port. No Mac ever
shipped with this GPU.

**Results so far: none on hardware.** Everything below is a documented candidate or an
experiment to run.

## Monterey (macOS 12): native Skylake drivers

Current candidate (`profiles/monterey/config-overlay.plist`, device `PciRoot(0x0)/Pci(0x2,0x0)`):

| Property | Value | Source / reason |
| --- | --- | --- |
| `AAPL,ig-platform-id` | `05003B19` (0x193B0005) | Dortania laptop/NUC Skylake table: "NUC, recommended for HD 580". WhateverGreen: Iris Pro 580 framebuffer, 4 connectors (LVDS + 3 DP), 34 MB stolen, FBMEM 0. |
| `device-id` | `27190000` (0x1927) | Upstream's last working state; their commit says it fixed "occasional Metal application crash … unknown MTLDevice" |
| `disable-agdc` | `01000000` | Upstream's last working state |
| `force-online` | `01000000` | Upstream; forces connectors online (hot-plug, wake) |
| boot-arg `forceRenderStandby=0` | — | WhateverGreen-documented fix for iGPU RC6 transitions panicking NVMe (seen upstream) |
| BIOS DVMT pre-alloc | 64 MB | Required by the framebuffer's stolen-memory size |

Removed from upstream: `enable-hdmi20` (WhateverGreen: not implemented on macOS 11+),
`enable-metal` (meant for offline/headless rendering), connector pipe/type patches (upstream
already withdrew them), and `hda-gfx` (WhateverGreen sets it automatically).

### A/B experiments (one change at a time; record per [hardware-testing.md](../hardware-testing.md))

| ID | Change against the candidate | Question it answers | Backlog |
| --- | --- | --- | --- |
| G-1 | Remove `device-id` (native `0x193B`) | Is the spoof still needed on Monterey's Metal stack? | [B-012](backlog.md#b-012) |
| G-2 | `device-id` = `12190000` (HD 530) | Upstream's older spoof (fixed a login-screen video bug) | B-012 |
| G-3 | Add `enable-metal` = `01000000` | Reproduce upstream exactly | B-012 |
| G-4 | Add `enable-lspcon-support` + `framebuffer-conN-has-lspcon` (N = HDMI connector index from IORegistryExplorer) | HDMI 2.0 4K60 through the PS175 | [B-013](backlog.md#b-013) |
| G-5 | Add `-igfxhdmidivs` (`enable-hdmi-dividers-fix`) | Hangs with high pixel-clock HDMI | B-013 |
| G-6 | Remove `force-online` / `disable-agdc` | Are they still needed? | [B-030](backlog.md#b-030) |
| G-7 | Remove `forceRenderStandby=0` | Is the NVMe panic still reproducible? | [B-031](backlog.md#b-031) |

To try one, edit the overlay on a branch, rebuild, and compare the generated `config.plist`
files (`diff`).

### Verifying real acceleration

Rendering a desktop proves nothing on its own. Check all of these (T-GFX-1…4):

* System Information → Graphics/Displays shows **Intel Iris Pro Graphics 580** (or the spoofed
  name), **VRAM 1536 MB**, and **Metal: Supported**. "7 MB VRAM" means no acceleration.
* `ioreg -l | grep -i "AAPL,ig-platform-id"` matches the configured value.
* `AppleIntelSKLGraphicsFramebuffer` and `AppleIntelSKLGraphics` are loaded.
* Dock and Mission Control animations are smooth, and a Metal benchmark runs.
* Hardware video decode works (HEVC/H.264).

## Ventura and later: Skylake drivers are gone

macOS 13 removed the SKL graphics kexts. WhateverGreen ≥ 1.6.1 can make the GPU load the
**Kaby Lake** drivers with a spoofed `device-id` and a KBL `AAPL,ig-platform-id`. The
WhateverGreen manual says to choose "the closest" KBL model and adds that "experiments are the
best practice". Nobody has shown this working on a **GT4e** part. Don't assume an HD 530 → HD 630
recipe carries over.

| Candidate | `device-id` | `AAPL,ig-platform-id` | Rationale |
| --- | --- | --- | --- |
| **KBL-A** (in `profiles/ventura/config-overlay.plist`) | `27590000` (0x5927, Iris Plus 650, GT3e) | `02002659` (0x59260002) | Closest KBL tier (GT3e + eDRAM); Dortania's NUC value for HD 640/650 |
| KBL-B | `12590000` (0x5912, HD 630) | `00001B59` (0x591B0000) | The common Skylake desktop recipe; Dortania's NUC value for HD 630 |

Both use `AAPL,GfxYTile = 01000000`, which WhateverGreen recommends for SKL→KBL spoofs.

Sequoia and Tahoe: whether the KBL framebuffer driver is still present and usable is an open
question ([B-042](backlog.md#b-042), [B-043](backlog.md#b-043)). The fallback is OpenCore Legacy
Patcher root patches, which have security implications
([compatibility.md](../compatibility.md#security-reducing-patches)).

## Known historical problems (upstream, Catalina/Big Sur beta)

* Wake from sleep → black screen until a display is replugged or power-cycled
  ([B-030](backlog.md#b-030)).
* NVMe kernel panics during iGPU low-power transitions (fixed with `forceRenderStandby=0`).
* Occasional Metal application crashes with the HD 530 spoof (changed to `0x1927`).
* Login-screen glitch with full-screen video and the native ID (changed to HD 530).

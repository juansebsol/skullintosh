"""Generate a codeless USB map kext from documented port data.

The map is an ``AppleUSBHostMergeProperties`` personality (no executable). It matches the xHCI
controller by PCI ID and the SMBIOS model, so it is regenerated for every profile.
"""

from __future__ import annotations

import plistlib
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from skullintosh.errors import SkullintoshError

# UsbConnector values from the ACPI _UPC spec as used by macOS.
CONNECTOR_TYPES = {
    0: "USB 2 Type-A",
    3: "USB 3 Type-A",
    8: "Type-C (USB 2 only)",
    9: "Type-C with switch",
    10: "Type-C without switch",
    255: "Internal",
}
_PORT_NAME_RE = re.compile(r"^(HS|SS|USR)\d{2}$")
_PCI_RE = re.compile(r"^([0-9a-f]{4}):([0-9a-f]{4})$")


@dataclass(frozen=True)
class Port:
    name: str
    port: int
    connector: int
    physical: str
    verified: bool


@dataclass(frozen=True)
class UsbMap:
    controller: str
    pci_vendor: str
    pci_device: str
    source: str
    verified: bool
    ports: tuple[Port, ...]

    @property
    def port_count(self) -> int:
        return max(p.port for p in self.ports)


def load_usb_map(path: Path) -> UsbMap:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise SkullintoshError(f"cannot read USB map {path}: {exc}") from exc
    ctrl = data.get("controller", {})
    match = _PCI_RE.match(str(ctrl.get("pci_id", "")).lower())
    if not match:
        raise SkullintoshError(f"{path}: controller.pci_id must look like 8086:a12f")
    ports = []
    seen_names, seen_numbers = set(), set()
    for raw in data.get("ports", []):
        name, number, connector = raw.get("name"), raw.get("port"), raw.get("connector")
        if not isinstance(name, str) or not _PORT_NAME_RE.match(name):
            raise SkullintoshError(f"{path}: invalid port name {name!r}")
        if not isinstance(number, int) or not 1 <= number <= 255:
            raise SkullintoshError(f"{path}: {name}: port must be an integer 1-255")
        if connector not in CONNECTOR_TYPES:
            raise SkullintoshError(f"{path}: {name}: unknown connector type {connector!r}")
        if name in seen_names or number in seen_numbers:
            raise SkullintoshError(f"{path}: duplicate port {name}/{number}")
        seen_names.add(name)
        seen_numbers.add(number)
        ports.append(
            Port(
                name,
                number,
                connector,
                raw.get("physical", "unknown"),
                bool(raw.get("verified", False)),
            )
        )
    if not ports:
        raise SkullintoshError(f"{path}: no ports defined")
    if len(ports) > 15:
        raise SkullintoshError(f"{path}: {len(ports)} ports exceeds macOS's 15-port limit")
    return UsbMap(
        ctrl.get("name", "XHC"),
        match.group(1),
        match.group(2),
        data.get("source", ""),
        bool(data.get("verified", False)),
        tuple(ports),
    )


def info_plist(usb: UsbMap, smbios_model: str) -> dict:
    ports = {
        p.name: {"UsbConnector": p.connector, "port": p.port.to_bytes(4, "little")}
        for p in usb.ports
    }
    personality = {
        "CFBundleIdentifier": "com.apple.driver.AppleUSBHostMergeProperties",
        "IOClass": "AppleUSBHostMergeProperties",
        "IOProviderClass": "AppleUSBXHCIPCI",
        "IOPCIPrimaryMatch": f"0x{usb.pci_device}{usb.pci_vendor}",
        "IOProviderMergeProperties": {
            "port-count": usb.port_count.to_bytes(4, "little"),
            "ports": ports,
        },
        "model": smbios_model,
    }
    return {
        "CFBundleDevelopmentRegion": "English",
        "CFBundleGetInfoString": f"Skullintosh codeless USB map ({usb.source})",
        "CFBundleIdentifier": "org.skullintosh.USBMap",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": "USBMap",
        "CFBundlePackageType": "KEXT",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleSignature": "????",
        "CFBundleVersion": "1.0.0",
        "IOKitPersonalities": {f"{usb.controller}-{smbios_model}": personality},
        "OSBundleRequired": "Root",
    }


def write_kext(usb: UsbMap, smbios_model: str, kexts_dir: Path) -> Path:
    bundle = kexts_dir / "USBMap.kext"
    contents = bundle / "Contents"
    contents.mkdir(parents=True, exist_ok=True)
    with open(contents / "Info.plist", "wb") as fh:
        plistlib.dump(info_plist(usb, smbios_model), fh, sort_keys=True)
    return bundle

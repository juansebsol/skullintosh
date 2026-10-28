import plistlib

import pytest

from skullintosh.errors import SkullintoshError
from skullintosh.usbmap import info_plist, load_usb_map, write_kext


def test_repository_map_is_provisional_and_valid(root):
    usb = load_usb_map(root / "hardware" / "usb" / "nuc6i7kyb.toml")
    assert usb.verified is False, "flip only after physical USB testing (docs/hardware-testing.md)"
    assert (usb.pci_vendor, usb.pci_device) == ("8086", "a12f")
    assert usb.port_count == 20
    assert {p.name for p in usb.ports} >= {"HS01", "SS01", "HS09"}


def test_generated_info_plist(root, tmp_path):
    usb = load_usb_map(root / "hardware" / "usb" / "nuc6i7kyb.toml")
    bundle = write_kext(usb, "iMac17,1", tmp_path)
    info = plistlib.loads((bundle / "Contents" / "Info.plist").read_bytes())
    personality = info["IOKitPersonalities"]["XHC-iMac17,1"]
    assert personality["IOPCIPrimaryMatch"] == "0xa12f8086"
    assert personality["model"] == "iMac17,1"
    ports = personality["IOProviderMergeProperties"]["ports"]
    assert ports["SS01"] == {"UsbConnector": 3, "port": bytes([17, 0, 0, 0])}
    assert ports["HS09"]["UsbConnector"] == 255
    assert "CFBundleExecutable" not in info  # codeless


def test_model_changes_the_personality(root):
    usb = load_usb_map(root / "hardware" / "usb" / "nuc6i7kyb.toml")
    assert "XHC-iMac18,1" in info_plist(usb, "iMac18,1")["IOKitPersonalities"]


@pytest.mark.parametrize(
    "body,match",
    [
        (
            '[controller]\npci_id="8086:a12f"\n[[ports]]\nname="HS01"\nport=1\nconnector=7\n',
            "connector",
        ),
        (
            '[controller]\npci_id="8086:a12f"\n[[ports]]\nname="XX01"\nport=1\nconnector=3\n',
            "port name",
        ),
        ('[controller]\npci_id="nope"\n', "pci_id"),
        (
            '[controller]\npci_id="8086:a12f"\n[[ports]]\nname="HS01"\nport=1\nconnector=3\n'
            '[[ports]]\nname="HS02"\nport=1\nconnector=3\n',
            "duplicate",
        ),
    ],
)
def test_rejects_bad_maps(tmp_path, body, match):
    path = tmp_path / "map.toml"
    path.write_text(body)
    with pytest.raises(SkullintoshError, match=match):
        load_usb_map(path)


def test_rejects_more_than_15_ports(tmp_path):
    ports = "".join(f'[[ports]]\nname="HS{i:02d}"\nport={i}\nconnector=3\n' for i in range(1, 17))
    path = tmp_path / "map.toml"
    path.write_text('[controller]\npci_id="8086:a12f"\n' + ports)
    with pytest.raises(SkullintoshError, match="15-port"):
        load_usb_map(path)

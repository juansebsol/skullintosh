import pytest

from skullintosh.errors import SkullintoshError
from skullintosh.overlay import apply_overlay, reset_owned


def sample():
    return {
        "ACPI": {"Add": [{"Path": "x"}], "Delete": [], "Patch": []},
        "Booter": {"MmioWhitelist": [], "Patch": [], "Quirks": {"SetupVirtualMap": True}},
        "DeviceProperties": {
            "Add": {"PciRoot(0x0)/Pci(0x1b,0x0)": {"layout-id": b"\1"}},
            "Delete": {},
        },
        "Kernel": {
            "Add": [1],
            "Block": [],
            "Force": [],
            "Patch": [],
            "Quirks": {"DisableIoMapper": False},
        },
        "Misc": {"Entries": [], "Tools": [], "Security": {"ScanPolicy": 1}},
        "NVRAM": {"Add": {"G": {"a": 1}}, "Delete": {}, "LegacySchema": {}},
        "UEFI": {"Drivers": [], "ReservedMemory": []},
    }


def test_merges_known_keys_and_drops_comments():
    cfg = sample()
    apply_overlay(cfg, {"Kernel": {"Quirks": {"DisableIoMapper": True, "#why": "x"}}}, "t")
    assert cfg["Kernel"]["Quirks"] == {"DisableIoMapper": True}


def test_unknown_key_fails():
    with pytest.raises(SkullintoshError, match="does not exist"):
        apply_overlay(sample(), {"Kernel": {"Quirks": {"DisableIOMapper": True}}}, "t")


def test_type_mismatch_fails():
    with pytest.raises(SkullintoshError, match="must be int"):
        apply_overlay(sample(), {"Misc": {"Security": {"ScanPolicy": "769"}}}, "t")


def test_bool_is_not_int():
    with pytest.raises(SkullintoshError):
        apply_overlay(sample(), {"Misc": {"Security": {"ScanPolicy": True}}}, "t")


def test_freeform_paths_accept_new_keys_and_strip_nested_comments():
    cfg = sample()
    reset_owned(cfg)
    apply_overlay(
        cfg,
        {
            "DeviceProperties": {
                "Add": {"PciRoot(0x0)/Pci(0x2,0x0)": {"device-id": b"\x27\x19\0\0", "#note": "x"}}
            }
        },
        "t",
    )
    assert cfg["DeviceProperties"]["Add"] == {
        "PciRoot(0x0)/Pci(0x2,0x0)": {"device-id": b"\x27\x19\0\0"}
    }


def test_reset_owned_clears_sample_content():
    cfg = sample()
    reset_owned(cfg)
    assert cfg["ACPI"]["Add"] == [] and cfg["Kernel"]["Add"] == []
    assert cfg["DeviceProperties"]["Add"] == {} and cfg["NVRAM"]["Add"] == {}
    assert cfg["Booter"]["Quirks"] == {"SetupVirtualMap": True}

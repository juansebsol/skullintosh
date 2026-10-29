# skullintosh: secret-scan-ignore-file  (contains deliberately fake identifiers)
from conftest import base_config, kext_entry, make_kext

from skullintosh.validate import (
    check_dual_boot_safety,
    check_identity,
    check_kexts,
    check_references,
    check_security,
)

LILU = "as.vit9696.Lilu"


def codes(findings, level="error"):
    return [f.code for f in findings if f.level == level]


def setup_kexts(tmp_path, entries, specs):
    oc = tmp_path / "EFI" / "OC"
    for spec in specs:
        make_kext(oc / "Kexts", **spec)
    cfg = base_config()
    cfg["Kernel"]["Add"] = entries
    return cfg, oc


def test_dependency_order_ok(tmp_path):
    cfg, oc = setup_kexts(
        tmp_path,
        [kext_entry("Lilu.kext"), kext_entry("WEG.kext")],
        [
            {"bundle": "Lilu.kext", "ident": LILU, "version": "1.7.2", "compatible": "1.2.0"},
            {"bundle": "WEG.kext", "ident": "x.weg", "libraries": {LILU: "1.2.0"}},
        ],
    )
    assert codes(check_kexts(cfg, oc)) == []


def test_dependency_loaded_too_late(tmp_path):
    cfg, oc = setup_kexts(
        tmp_path,
        [kext_entry("WEG.kext"), kext_entry("Lilu.kext")],
        [
            {"bundle": "Lilu.kext", "ident": LILU, "version": "1.7.2"},
            {"bundle": "WEG.kext", "ident": "x.weg", "libraries": {LILU: "1.2.0"}},
        ],
    )
    assert codes(check_kexts(cfg, oc)) == ["kext-order"]


def test_missing_and_disabled_dependency(tmp_path):
    cfg, oc = setup_kexts(
        tmp_path,
        [kext_entry("Lilu.kext", enabled=False), kext_entry("WEG.kext")],
        [
            {"bundle": "Lilu.kext", "ident": LILU, "version": "1.7.2"},
            {"bundle": "WEG.kext", "ident": "x.weg", "libraries": {LILU: "1.2.0"}},
        ],
    )
    assert codes(check_kexts(cfg, oc)) == ["kext-dependency"]


def test_dependency_version_too_old(tmp_path):
    cfg, oc = setup_kexts(
        tmp_path,
        [kext_entry("Lilu.kext"), kext_entry("WEG.kext")],
        [
            {"bundle": "Lilu.kext", "ident": LILU, "version": "1.1.0"},
            {"bundle": "WEG.kext", "ident": "x.weg", "libraries": {LILU: "1.2.0"}},
        ],
    )
    assert codes(check_kexts(cfg, oc)) == ["kext-version"]


def test_wifi_kexts_conflict_only_when_ranges_overlap(tmp_path):
    specs = [
        {"bundle": "itlwm.kext", "ident": "com.zxystd.itlwm"},
        {"bundle": "AirportItlwm.kext", "ident": "com.zxystd.AirportItlwm"},
    ]
    cfg, oc = setup_kexts(
        tmp_path,
        [kext_entry("itlwm.kext"), kext_entry("AirportItlwm.kext", lo="21.0.0", hi="21.99.99")],
        specs,
    )
    assert codes(check_kexts(cfg, oc)) == ["wifi-conflict"]
    cfg["Kernel"]["Add"][0]["MinKernel"] = "22.0.0"
    assert codes(check_kexts(cfg, oc)) == []


def test_bluetooth_rules(tmp_path):
    cfg, oc = setup_kexts(
        tmp_path,
        [kext_entry("IntelBluetoothFirmware.kext"), kext_entry("IntelBluetoothInjector.kext")],
        [
            {"bundle": "IntelBluetoothFirmware.kext", "ident": "a.ibf"},
            {"bundle": "IntelBluetoothInjector.kext", "ident": "a.ibi"},
        ],
    )
    assert sorted(codes(check_kexts(cfg, oc))) == ["bluetooth-fixup", "bluetooth-injector"]


def test_references_detect_missing_and_unreferenced_files(tmp_path):
    oc = tmp_path / "EFI" / "OC"
    (oc / "ACPI").mkdir(parents=True)
    (oc / "ACPI" / "SSDT-EXTRA.aml").write_bytes(b"x")
    (oc / "Drivers").mkdir()
    cfg = base_config()
    cfg["ACPI"]["Add"] = [{"Path": "SSDT-PLUG.aml"}]
    cfg["UEFI"]["Drivers"] = [{"Path": "OpenRuntime.efi"}]
    found = check_references(cfg, oc)
    assert codes(found) == ["missing-file", "missing-file"]
    assert codes(found, "warning") == ["unreferenced-file"]


def test_duplicate_kext_rejected(tmp_path):
    cfg, oc = setup_kexts(
        tmp_path,
        [kext_entry("Lilu.kext"), kext_entry("Lilu.kext")],
        [{"bundle": "Lilu.kext", "ident": LILU}],
    )
    assert "duplicate-kext" in codes(check_references(cfg, oc))


def test_security_relaxations_rejected():
    cfg = base_config()
    assert check_security(cfg) == []
    nv = cfg["NVRAM"]["Add"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"]
    nv["csr-active-config"] = b"\x03\0\0\0"
    nv["boot-args"] = "-v amfi_get_out_of_my_way=1"
    cfg["Misc"]["Security"]["SecureBootModel"] = "Disabled"
    assert sorted(codes(check_security(cfg))) == [
        "secure-boot-disabled",
        "security-boot-arg",
        "sip-relaxed",
    ]


def test_dual_boot_safety():
    cfg = base_config()
    assert codes(check_dual_boot_safety(cfg)) == []
    cfg["Misc"]["Security"]["ScanPolicy"] = 0
    cfg["Misc"]["Boot"]["LauncherOption"] = "Full"
    cfg["UEFI"]["Quirks"]["RequestBootVarRouting"] = False
    assert codes(check_dual_boot_safety(cfg)) == ["boot-order", "boot-order", "scan-policy"]
    cfg = base_config()
    cfg["Misc"]["Security"]["ScanPolicy"] = 769 | 0x400  # EFI System Partitions
    assert codes(check_dual_boot_safety(cfg)) == ["scan-policy"]
    cfg["Misc"]["Security"]["ScanPolicy"] = 769 | 0x1000  # Linux root
    assert codes(check_dual_boot_safety(cfg)) == ["scan-policy"]


def test_fat32_installer_scan_policy_is_a_warning_unless_ntfs_driver_loaded():
    cfg = base_config()
    cfg["Misc"]["Security"]["ScanPolicy"] = 2817  # 769 + Msft Basic Data
    found = check_dual_boot_safety(cfg)
    assert codes(found) == [] and codes(found, "warning") == ["scan-policy"]
    cfg["UEFI"]["Drivers"] = [{"Path": "OpenNtfsDxe.efi", "Enabled": True}]
    assert codes(check_dual_boot_safety(cfg)) == ["scan-policy"]


def test_nvram_reset_must_preserve_boot_entries():
    cfg = base_config()
    entry = {"Path": "ResetNvramEntry.efi", "Enabled": True, "Arguments": ""}
    cfg["UEFI"]["Drivers"] = [entry]
    assert codes(check_dual_boot_safety(cfg)) == ["nvram-reset"]
    entry["Arguments"] = "--preserve-boot"
    assert codes(check_dual_boot_safety(cfg)) == []
    entry["Arguments"] = "--preserve-boot --apple"
    assert codes(check_dual_boot_safety(cfg)) == ["nvram-reset"]


def test_secure_boot_needs_nonzero_system_id():
    cfg = base_config()
    assert "secure-boot-id" not in codes(check_security(cfg))
    cfg["PlatformInfo"]["Generic"]["SystemUUID"] = "00000000-0000-0000-0000-000000000000"
    assert "secure-boot-id" in codes(check_security(cfg))
    cfg["Misc"]["Security"]["ApECID"] = 1234
    assert "secure-boot-id" not in codes(check_security(cfg))


def test_identity_leak_detected(tmp_path):
    cfg = base_config()
    assert check_identity(cfg, tmp_path, {"personalized": False}) == []
    cfg["PlatformInfo"]["Generic"]["SystemSerialNumber"] = "C02AAAAAAAAA"
    assert codes(check_identity(cfg, tmp_path, {"personalized": False})) == ["identity-leak"]
    assert codes(check_identity(cfg, tmp_path, {"personalized": True})) == ["identity"]


def test_unreadable_kext_plist_is_a_finding_not_a_crash(tmp_path):
    cfg, oc = setup_kexts(
        tmp_path, [kext_entry("Lilu.kext")], [{"bundle": "Lilu.kext", "ident": LILU}]
    )
    (oc / "Kexts" / "Lilu.kext" / "Contents" / "Info.plist").write_bytes(b"garbage")
    assert codes(check_kexts(cfg, oc)) == ["kext-plist"]

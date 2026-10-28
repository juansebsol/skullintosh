# skullintosh: secret-scan-ignore-file  (this file contains deliberately fake identifiers)
import tomllib

from skullintosh.report import environment_report, inventory_report, reconcile, sanitize

RAW = """\
System Information
	Manufacturer: Intel Corporation
	Product Name: NUC6i7KYK
	Serial Number: G6KY12345678
	UUID: 3F1A2B4C-5D6E-4F70-8192-A3B4C5D6E7F8
00:02.0 VGA compatible controller [0300]: Intel Corporation Iris Pro Graphics 580 [8086:193b]
00:1f.6 Ethernet controller [0200]: Intel Corporation Ethernet Connection I219-LM [8086:156f]
link/ether 3c:22:fb:12:34:56 brd ff:ff:ff:ff:ff:ff
inet 192.168.1.23/24
Bus 001 Device 004: ID 8087:0a2b Intel Corp. Bluetooth wireless interface
USB\\VID_0781&PID_5581\\4C530001231122108455
/home/alice/skullintosh
Codec: Realtek ALC233
Vendor Id: 0x10ec0233
ESP type C12A7328-F81F-11D2-BA4B-00A0C93EC93B
"""


def test_sanitize_masks_identifiers():
    out = sanitize(RAW)
    for secret in (
        "G6KY12345678",
        "3F1A2B4C-5D6E",
        "3c:22:fb",
        "192.168.1.23",
        "4C530001231122108455",
        "alice",
    ):
        assert secret not in out, secret
    assert "Serial Number: <redacted>" in out
    assert "C12A7328-F81F-11D2-BA4B-00A0C93EC93B" in out  # public GPT type GUID kept
    assert "[8086:193b]" in out


def test_reconcile_against_reference(root):
    reference = tomllib.loads((root / "hardware/reference/nuc6i7kyk.toml").read_text())
    rows = {name: status for name, _exp, status, _need in reconcile(sanitize(RAW), reference)}
    assert rows["Iris Pro Graphics 580 (GT4e)"].startswith("found")
    assert rows["Intel 8260 Bluetooth (USB)"].startswith("found")
    assert rows["Realtek ALC233 codec"].startswith("found")
    assert rows["Intel Dual Band Wireless-AC 8260"] == "NOT FOUND"
    assert rows["SDXC card reader"] == "record manually"


def test_windows_ids_are_recognised(root):
    reference = tomllib.loads((root / "hardware/reference/nuc6i7kyk.toml").read_text())
    text = (
        "PCI\\VEN_8086&DEV_24F3&SUBSYS_00108086&REV_3A\\4&1234&0&00E4\n"
        "HDAUDIO\\FUNC_01&VEN_10EC&DEV_0233&SUBSYS_80860000\n"
    )
    rows = {n: s for n, _e, s, _x in reconcile(text, reference)}
    assert rows["Intel Dual Band Wireless-AC 8260"].startswith("found")
    assert rows["Realtek ALC233 codec"].startswith("found")


def test_inventory_report_skips_binary_tables(root, tmp_path):
    (tmp_path / "lspci.txt").write_text(RAW)
    (tmp_path / "MSDM.dat").write_bytes(b"product key table")
    report = inventory_report(root, [tmp_path])
    assert "MSDM" not in report and "G6KY12345678" not in report
    assert "| Iris Pro Graphics 580 (GT4e) |" in report


def test_environment_report_has_no_home_path(root):
    import pathlib

    report = environment_report(root)
    assert str(pathlib.Path.home()) not in report
    assert "monterey" in report

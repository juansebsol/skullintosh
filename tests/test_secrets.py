# skullintosh: secret-scan-ignore-file  (this file contains deliberately fake identifiers)
import pytest

from skullintosh.errors import SkullintoshError
from skullintosh.identity import PLACEHOLDERS, load_identity
from skullintosh.secretscan import candidate_files, scan_paths, scan_text


def kinds(text):
    return [h.kind for h in scan_text(text, "f")]


def test_placeholders_and_masks_are_allowed():
    text = (
        "<key>SystemSerialNumber</key>\n<string>W00000000001</string>\n"
        "<key>MLB</key><string>M0000000000000001</string>\n"
        'SystemSerialNumber = "C02XXXXXXXXX"\nMAC: XX:XX:XX:XX:XX:XX 00:00:00:00:00:00\n'
        "SystemUUID: 00000000-0000-0000-0000-000000000000\n"
    )
    assert kinds(text) == []


def test_real_looking_values_are_found():
    assert kinds("<key>SystemSerialNumber</key>\n\t<string>C02TQ1XYJ1GJ</string>") == ["smbios"]
    assert kinds('MLB = "C02734205J9GK4XAB"') == ["serial/uuid"]
    assert kinds("ether 3c:22:fb:12:34:56") == ["mac-address"]
    assert kinds("key ABCDE-12345-FGHIJ-67890-KLMNO") == ["product-key"]
    assert kinds("IdentifyingNumber : G6KY1234567") == ["serial/uuid"]


def test_line_pragma_suppresses():
    assert kinds("ether 3c:22:fb:12:34:56  # skullintosh: allow-secret") == []


def test_non_mac_hex_is_ignored():
    assert kinds("PciRoot(0x0)/Pci(0x1f,0x3) 8086:a12f 2024-06-09T07:01:41") == []


def test_repository_is_clean(root):
    hits = scan_paths(candidate_files(root), root)
    assert hits == [], "\n".join(map(str, hits))


def _identity_file(tmp_path, **overrides):
    values = {
        "SystemSerialNumber": "C02TQ1XYJ1GJ",
        "MLB": "C02734205J9GK4XAB",
        "SystemUUID": "3F1A2B4C-5D6E-4F70-8192-A3B4C5D6E7F8",
        "ROM": "a1b2c3d4e5f6",
    }
    values.update(overrides)
    path = tmp_path / "smbios.toml"
    path.write_text("".join(f'{k} = "{v}"\n' for k, v in values.items()))
    return path


def test_identity_file_is_validated(tmp_path):
    identity = load_identity(_identity_file(tmp_path))
    assert identity["ROM"] == bytes.fromhex("a1b2c3d4e5f6")
    with pytest.raises(SkullintoshError, match="placeholder"):
        load_identity(
            _identity_file(tmp_path, SystemSerialNumber=PLACEHOLDERS["SystemSerialNumber"])
        )
    with pytest.raises(SkullintoshError, match="ROM"):
        load_identity(_identity_file(tmp_path, ROM="xyz"))

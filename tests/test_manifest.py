import pytest

from skullintosh.errors import SkullintoshError
from skullintosh.manifest import load_manifest


def test_repository_manifest_is_complete(root):
    manifest = load_manifest(root / "manifests" / "dependencies.toml")
    assert "opencore" in manifest.packages
    for package in manifest.packages.values():
        assert package.owner in manifest.approved_owners
        for asset in package.assets.values():
            assert len(asset.sha256) == 64
            assert asset.url.startswith(f"https://github.com/{package.repo}/releases/download/")


def test_opencore_has_matching_release_and_debug(root):
    manifest = load_manifest(root / "manifests" / "dependencies.toml")
    oc = manifest.package("opencore")
    assert set(oc.assets) == {"release", "debug"}
    assert all(oc.tag in a.name for a in oc.assets.values())


def test_every_package_has_a_license_text(root):
    manifest = load_manifest(root / "manifests" / "dependencies.toml")
    for pid in manifest.packages:
        assert (root / "licenses" / f"{pid}.txt").is_file(), pid


def test_airportitlwm_variants_are_os_bound(root):
    manifest = load_manifest(root / "manifests" / "dependencies.toml")
    for kid, kext in manifest.kexts.items():
        if kid.startswith("AirportItlwm-"):
            assert kext.darwin_min is not None and kext.darwin_max is not None
            assert kext.group == "wifi"


def _write(tmp_path, body):
    path = tmp_path / "m.toml"
    path.write_text(body)
    return path


def test_rejects_unapproved_owner(tmp_path):
    path = _write(
        tmp_path,
        """
schema = 1
approved_owners = ["acidanthera"]
[packages.x]
repo = "someone/Thing"
tag = "1"
license = "MIT"
assets.release = { name = "x.zip", sha256 = "%s" }
"""
        % ("a" * 64),
    )
    with pytest.raises(SkullintoshError, match="approved_owners"):
        load_manifest(path)


def test_rejects_missing_hash(tmp_path):
    path = _write(
        tmp_path,
        """
schema = 1
approved_owners = ["acidanthera"]
[packages.x]
repo = "acidanthera/Thing"
tag = "1"
license = "MIT"
assets.release = { name = "x.zip", sha256 = "" }
""",
    )
    with pytest.raises(SkullintoshError, match="no sha256"):
        load_manifest(path)
    assert load_manifest(path, require_hashes=False).packages["x"]


def test_rejects_path_in_asset_name(tmp_path):
    path = _write(
        tmp_path,
        """
schema = 1
approved_owners = ["acidanthera"]
[packages.x]
repo = "acidanthera/Thing"
tag = "1"
license = "MIT"
assets.release = { name = "../evil.zip", sha256 = "%s" }
"""
        % ("a" * 64),
    )
    with pytest.raises(SkullintoshError, match="invalid name"):
        load_manifest(path)

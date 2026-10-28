import stat
import zipfile

import pytest

from skullintosh.errors import SkullintoshError
from skullintosh.util import (
    deterministic_zip,
    extract_member_tree,
    kernel_ranges_overlap,
    sha256_file,
    version_ge,
)


def test_deterministic_zip_is_stable(tmp_path):
    src = tmp_path / "src"
    (src / "a" / "b").mkdir(parents=True)
    (src / "a" / "b" / "f.txt").write_text("hello")
    (src / "z.bin").write_bytes(b"\0" * 10)
    one, two = tmp_path / "1.zip", tmp_path / "2.zip"
    deterministic_zip(src, one)
    (src / "z.bin").touch()  # mtime change must not matter
    deterministic_zip(src, two)
    assert sha256_file(one) == sha256_file(two)
    names = zipfile.ZipFile(one).namelist()
    assert names == sorted(names)


def _zip(tmp_path, entries):
    path = tmp_path / "in.zip"
    with zipfile.ZipFile(path, "w") as zf:
        for name, data, mode in entries:
            info = zipfile.ZipInfo(name)
            info.external_attr = mode << 16
            zf.writestr(info, data)
    return path


def test_extract_member_tree(tmp_path):
    path = _zip(
        tmp_path,
        [
            ("Kexts/A.kext/Contents/Info.plist", b"x", stat.S_IFREG | 0o644),
            ("Kexts/A.kext/Contents/MacOS/A", b"y", stat.S_IFREG | 0o755),
            ("Kexts/B.kext/Contents/Info.plist", b"z", stat.S_IFREG | 0o644),
        ],
    )
    with zipfile.ZipFile(path) as zf:
        extract_member_tree(zf, "Kexts/A.kext", tmp_path / "out")
    assert (tmp_path / "out/A.kext/Contents/MacOS/A").read_bytes() == b"y"
    assert not (tmp_path / "out/B.kext").exists()


@pytest.mark.parametrize(
    "name,mode",
    [
        ("../evil/x", stat.S_IFREG | 0o644),
        ("A.kext/link", stat.S_IFLNK | 0o777),
    ],
)
def test_extract_rejects_unsafe_members(tmp_path, name, mode):
    member = name.split("/")[0] if not name.startswith("..") else name
    path = _zip(tmp_path, [(name, b"x", mode)])
    with zipfile.ZipFile(path) as zf, pytest.raises(SkullintoshError):
        extract_member_tree(zf, member, tmp_path / "out")


def test_versions_and_kernel_ranges():
    assert version_ge("1.7.2", "1.2.0") and version_ge("v2.3.0", "2.3")
    assert not version_ge("1.1.9", "1.2.0")
    assert kernel_ranges_overlap(("21.0.0", "21.99.99"), ("", ""))
    assert not kernel_ranges_overlap(("21.0.0", "21.99.99"), ("22.0.0", ""))
    assert kernel_ranges_overlap(("23.0.0", "23.3.99"), ("23.3.0", "23.99.99"))

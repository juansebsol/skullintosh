"""Repository hygiene: every plist/TOML parses and scripts follow the safety conventions."""

import plistlib
import re
import tomllib

SKIP = {".git", ".venv", "build", "dist", ".cache"}


def repo_files(root, pattern):
    return [p for p in root.rglob(pattern) if not SKIP & set(p.relative_to(root).parts)]


def test_all_plists_parse(root):
    plists = repo_files(root, "*.plist")
    assert plists
    for path in plists:
        with open(path, "rb") as fh:
            assert isinstance(plistlib.load(fh), dict), path


def test_all_toml_parses(root):
    for path in repo_files(root, "*.toml"):
        tomllib.loads(path.read_text(encoding="utf-8"))


def test_shell_scripts_are_strict_and_never_write_disks(root):
    forbidden = (
        "mkfs",
        "diskutil erase",
        "efibootmgr -c",
        "efibootmgr -o",
        "efibootmgr -B",
        "efibootmgr --create",
        "parted ",
        "sgdisk ",
        "wipefs",
    )
    for path in repo_files(root, "*.sh"):
        text = path.read_text()
        assert "set -euo pipefail" in text, path
        assert not re.search(r"(^|[\s;|&])dd\s", text), f"{path} uses dd"
        for bad in forbidden:
            assert bad not in text, f"{path} contains {bad!r}"


def test_powershell_scripts_never_change_boot_config(root):
    forbidden = (
        "bcdedit /set",
        "bcdedit /delete",
        "bcdedit /import",
        "bcdedit /create",
        "Format-Volume",
        "Clear-Disk",
        "Remove-Partition",
        "Initialize-Disk",
    )
    for path in repo_files(root, "*.ps1"):
        text = path.read_text()
        assert "Set-StrictMode" in text, path
        for bad in forbidden:
            assert bad.lower() not in text.lower(), f"{path} contains {bad!r}"

"""Find machine-specific identifiers that must never be committed or shared.

Looks for SMBIOS serials/MLB/UUID/ROM values, MAC addresses, Windows product keys and system
UUIDs in text files. Placeholders and masked values (``XXXX``, ``<redacted>``) are allowed. A
line can opt out with ``skullintosh: allow-secret``; a file can opt out in its first 5 lines
with ``skullintosh: secret-scan-ignore-file``.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from skullintosh.identity import PLACEHOLDERS

LINE_PRAGMA = "skullintosh: allow-secret"
FILE_PRAGMA = "skullintosh: secret-scan-ignore-file"
SKIP_DIRS = {
    ".git",
    ".cache",
    "build",
    "dist",
    ".venv",
    "venv",
    "__pycache__",
    "local",
    ".pytest_cache",
    ".ruff_cache",
}
MAX_BYTES = 2 * 1024 * 1024

_PLACEHOLDER_TEXT = {str(v).upper() for v in PLACEHOLDERS.values() if isinstance(v, str)} | {
    "112233445566",
    "ESHENRFV",
    "NULL",
    "",
    "<DATA>",
    "ZERO",
}
_MASKED = re.compile(r"X{3,}|<[^>]*>|REDACTED|\*{3,}|\.\.\.", re.IGNORECASE)

_SMBIOS_KEYS = r"SystemSerialNumber|MLB|SystemUUID|BoardSerialNumber|ChassisSerialNumber"
_PLIST_KV = re.compile(
    rf"<key>({_SMBIOS_KEYS}|ROM)</key>\s*<(string|data)>\s*([^<]*?)\s*</\2>", re.DOTALL
)
_TEXT_KV = re.compile(
    rf"\b({_SMBIOS_KEYS}|Serial\s?Number|IdentifyingNumber|system-uuid|System UUID)\b"
    r"[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9-]{6,})",
    re.IGNORECASE,
)
_MAC = re.compile(
    r"(?<![0-9A-Fa-f:-])(?:[0-9A-Fa-f]{2}([:-]))(?:[0-9A-Fa-f]{2}\1){4}"
    r"[0-9A-Fa-f]{2}(?![0-9A-Fa-f:-])"
)
_ALLOWED_MACS = {"00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF", "11:22:33:44:55:66"}
_PRODUCT_KEY = re.compile(r"\b[A-Z0-9]{5}(?:-[A-Z0-9]{5}){4}\b")


@dataclass(frozen=True)
class Hit:
    path: str
    line: int
    kind: str
    detail: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.kind}: {self.detail}"


def _allowed_value(value: str) -> bool:
    v = value.strip().upper()
    if v in _PLACEHOLDER_TEXT or _MASKED.search(value):
        return True
    if not any(c.isdigit() for c in v):
        return True  # identifiers always contain digits; this is a word or variable name
    return set(v.replace("-", "")) <= {"0"}


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def scan_text(text: str, path: str) -> list[Hit]:
    head = "\n".join(text.splitlines()[:5])
    if FILE_PRAGMA in head:
        return []
    lines = text.splitlines()

    def suppressed(lineno: int) -> bool:
        return 0 < lineno <= len(lines) and LINE_PRAGMA in lines[lineno - 1]

    hits: list[Hit] = []
    for m in _PLIST_KV.finditer(text):
        key, value = m.group(1), m.group(3)
        lineno = _line_of(text, m.start(3))
        if key == "ROM" and m.group(2) == "data":
            continue  # base64 data; checked by the config validator instead
        if not _allowed_value(value) and not suppressed(lineno):
            hits.append(Hit(path, lineno, "smbios", f"{key} has a non-placeholder value"))
    for m in _TEXT_KV.finditer(text):
        lineno = _line_of(text, m.start())
        if not _allowed_value(m.group(2)) and not suppressed(lineno):
            hits.append(Hit(path, lineno, "serial/uuid", f"{m.group(1)} looks like a real value"))
    for m in _MAC.finditer(text):
        lineno = _line_of(text, m.start())
        mac = m.group(0).upper().replace("-", ":")
        if mac not in _ALLOWED_MACS and not suppressed(lineno):
            hits.append(Hit(path, lineno, "mac-address", "unmasked MAC address"))
    for m in _PRODUCT_KEY.finditer(text):
        lineno = _line_of(text, m.start())
        if not suppressed(lineno):
            hits.append(Hit(path, lineno, "product-key", "looks like a Windows product key"))
    return hits


def candidate_files(root: Path) -> list[Path]:
    """Tracked and untracked-but-not-ignored files, or a directory walk without git."""
    try:
        out = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            check=True,
            capture_output=True,
        ).stdout
        files = [root / p for p in out.decode().split("\0") if p]
    except (OSError, subprocess.CalledProcessError):
        files = [
            p
            for p in root.rglob("*")
            if p.is_file() and not SKIP_DIRS.intersection(p.relative_to(root).parts)
        ]
    return sorted(f for f in files if f.is_file())


def scan_paths(paths: list[Path], root: Path) -> list[Hit]:
    hits: list[Hit] = []
    for path in paths:
        try:
            if path.stat().st_size > MAX_BYTES:
                continue
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:8192]:
            continue
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = str(path)
        hits.extend(scan_text(data.decode("utf-8", errors="replace"), rel))
    return hits

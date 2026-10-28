"""Small shared helpers: hashing, safe extraction, deterministic archives, versions."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

from skullintosh.errors import SkullintoshError

# 1980-01-01, the earliest timestamp a zip entry can carry.
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_repo_root(start: Path | None = None) -> Path:
    """Walk upwards from ``start`` until the dependency manifest is found."""
    env = os.environ.get("SKULLINTOSH_ROOT")
    if env:
        return Path(env).resolve()
    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "manifests" / "dependencies.toml").is_file():
            return candidate
    raise SkullintoshError(
        "could not find the Skullintosh repository root (manifests/dependencies.toml); "
        "run from inside the checkout or set SKULLINTOSH_ROOT"
    )


def _check_member_name(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        raise SkullintoshError(f"refusing unsafe archive member path: {name!r}")
    return path


def extract_member_tree(archive: zipfile.ZipFile, member: str, dest: Path) -> list[Path]:
    """Extract ``member`` (a file or a directory prefix) from ``archive`` into ``dest``.

    The member's final path component becomes ``dest / basename``. Symlinks and path traversal
    are rejected because archives are untrusted input.
    """
    member = member.rstrip("/")
    prefix = member + "/"
    matches = [
        i
        for i in archive.infolist()
        if i.filename in (member, prefix) or i.filename.startswith(prefix)
    ]
    if not matches:
        raise SkullintoshError(f"{member!r} not found in {archive.filename}")
    base = PurePosixPath(member).parent
    written: list[Path] = []
    for info in sorted(matches, key=lambda i: i.filename):
        rel = _check_member_name(info.filename).relative_to(base)
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise SkullintoshError(f"refusing symlink in archive: {info.filename}")
        target = dest.joinpath(*rel.parts)
        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as src, open(target, "wb") as out:
            while chunk := src.read(1 << 20):
                out.write(chunk)
        target.chmod(0o755 if mode & 0o111 else 0o644)
        written.append(target)
    return written


def deterministic_zip(source: Path, out_path: Path, *, prefix: str = "") -> None:
    """Zip ``source`` with sorted entries, fixed timestamps and normalised permissions."""
    entries = sorted(p for p in source.rglob("*"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in entries:
            rel = path.relative_to(source).as_posix()
            name = f"{prefix}{rel}"
            if path.is_symlink():
                raise SkullintoshError(f"refusing to archive symlink {path}")
            if path.is_dir():
                info = zipfile.ZipInfo(name + "/", date_time=ZIP_EPOCH)
                info.external_attr = (stat.S_IFDIR | 0o755) << 16
                zf.writestr(info, b"")
                continue
            info = zipfile.ZipInfo(name, date_time=ZIP_EPOCH)
            mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes(), compresslevel=9)


def tree_digest(root: Path) -> dict[str, str]:
    """Map every file under ``root`` (posix relative path) to its SHA-256."""
    return {
        p.relative_to(root).as_posix(): sha256_file(p)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


_VERSION_RE = re.compile(r"\d+")


def parse_version(text: str) -> tuple[int, ...]:
    """Parse loose versions like ``1.7.2``, ``v2.3.0`` or ``1.0``."""
    parts = tuple(int(x) for x in _VERSION_RE.findall(str(text)))
    return parts or (0,)


def version_ge(a: str, b: str) -> bool:
    pa, pb = parse_version(a), parse_version(b)
    width = max(len(pa), len(pb))
    return pa + (0,) * (width - len(pa)) >= pb + (0,) * (width - len(pb))


def kernel_bounds(darwin_min: int | None, darwin_max: int | None) -> tuple[str, str]:
    """OpenCore MinKernel/MaxKernel strings for a darwin major range."""
    lo = f"{darwin_min}.0.0" if darwin_min is not None else ""
    hi = f"{darwin_max}.99.99" if darwin_max is not None else ""
    return lo, hi


def parse_kernel(text: str) -> tuple[int, int, int] | None:
    if not text:
        return None
    nums = [int(x) for x in text.split(".")] + [0, 0]
    return nums[0], nums[1], nums[2]


def kernel_ranges_overlap(a: tuple[str, str], b: tuple[str, str]) -> bool:
    """Whether two (MinKernel, MaxKernel) ranges overlap; empty bounds are open."""
    lo_a, hi_a = parse_kernel(a[0]) or (0, 0, 0), parse_kernel(a[1]) or (999, 99, 99)
    lo_b, hi_b = parse_kernel(b[0]) or (0, 0, 0), parse_kernel(b[1]) or (999, 99, 99)
    return lo_a <= hi_b and lo_b <= hi_a


def relpath_for_display(path: Path) -> str:
    """Show paths without leaking the user's home directory."""
    home = str(Path.home())
    text = str(path)
    return "~" + text[len(home) :] if home and text.startswith(home) else text

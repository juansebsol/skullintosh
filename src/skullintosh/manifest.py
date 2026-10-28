"""The versioned dependency manifest (``manifests/dependencies.toml``)."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from skullintosh.errors import SkullintoshError

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REPO_RE = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class Asset:
    package: str
    key: str
    name: str
    sha256: str
    url: str


@dataclass(frozen=True)
class Package:
    id: str
    repo: str
    tag: str
    license: str
    assets: dict[str, Asset]

    @property
    def owner(self) -> str:
        return self.repo.split("/", 1)[0]

    @property
    def source_url(self) -> str:
        return f"https://github.com/{self.repo}/tree/{self.tag}"


@dataclass(frozen=True)
class Kext:
    id: str
    package: str
    path: str
    asset: str | None = None
    darwin_min: int | None = None
    darwin_max: int | None = None
    min_kernel: str | None = None
    max_kernel: str | None = None
    group: str | None = None

    @property
    def bundle_name(self) -> str:
        return self.path.rstrip("/").rsplit("/", 1)[-1]

    def applies_to(self, darwin: int) -> bool:
        if self.darwin_min is not None and darwin < self.darwin_min:
            return False
        return not (self.darwin_max is not None and darwin > self.darwin_max)


@dataclass(frozen=True)
class Manifest:
    path: Path
    approved_owners: tuple[str, ...]
    packages: dict[str, Package]
    kexts: dict[str, Kext] = field(default_factory=dict)

    def asset_for(self, package_id: str, key: str) -> Asset:
        package = self.package(package_id)
        if key not in package.assets:
            raise SkullintoshError(
                f"package {package_id!r} has no asset {key!r} (has: {', '.join(package.assets)})"
            )
        return package.assets[key]

    def package(self, package_id: str) -> Package:
        try:
            return self.packages[package_id]
        except KeyError:
            raise SkullintoshError(f"unknown package {package_id!r} in manifest") from None

    def kext(self, kext_id: str) -> Kext:
        try:
            return self.kexts[kext_id]
        except KeyError:
            raise SkullintoshError(f"unknown kext {kext_id!r} in manifest") from None

    def kext_asset(self, kext: Kext, flavor: str) -> Asset:
        package = self.package(kext.package)
        key = kext.asset or (flavor if flavor in package.assets else "release")
        return self.asset_for(kext.package, key)


def load_manifest(path: Path, *, require_hashes: bool = True) -> Manifest:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise SkullintoshError(f"cannot read manifest {path}: {exc}") from exc
    if data.get("schema") != 1:
        raise SkullintoshError(f"{path}: unsupported manifest schema {data.get('schema')!r}")

    owners = tuple(data.get("approved_owners", ()))
    packages: dict[str, Package] = {}
    for pid, raw in data.get("packages", {}).items():
        repo = raw.get("repo", "")
        if not _REPO_RE.match(repo):
            raise SkullintoshError(f"package {pid}: invalid repo {repo!r}")
        if repo.split("/", 1)[0] not in owners:
            raise SkullintoshError(f"package {pid}: owner of {repo} is not in approved_owners")
        for key in ("tag", "license"):
            if not raw.get(key):
                raise SkullintoshError(f"package {pid}: missing {key}")
        assets = {}
        for key, a in raw.get("assets", {}).items():
            name, sha = a.get("name", ""), a.get("sha256", "")
            if not name or "/" in name:
                raise SkullintoshError(f"package {pid} asset {key}: invalid name {name!r}")
            if sha and not _SHA256_RE.match(sha):
                raise SkullintoshError(f"package {pid} asset {key}: malformed sha256")
            if require_hashes and not sha:
                raise SkullintoshError(
                    f"package {pid} asset {key} has no sha256; run `skullintosh pin {pid}`"
                )
            url = f"https://github.com/{repo}/releases/download/{raw['tag']}/{name}"
            assets[key] = Asset(pid, key, name, sha, url)
        if not assets:
            raise SkullintoshError(f"package {pid}: no assets")
        packages[pid] = Package(pid, repo, raw["tag"], raw["license"], assets)

    kexts: dict[str, Kext] = {}
    for kid, raw in data.get("kexts", {}).items():
        allowed = {
            "package",
            "path",
            "asset",
            "darwin_min",
            "darwin_max",
            "min_kernel",
            "max_kernel",
            "group",
        }
        unknown = set(raw) - allowed
        if unknown:
            raise SkullintoshError(f"kext {kid}: unknown keys {sorted(unknown)}")
        if raw.get("package") not in packages:
            raise SkullintoshError(f"kext {kid}: unknown package {raw.get('package')!r}")
        if not str(raw.get("path", "")).endswith(".kext"):
            raise SkullintoshError(f"kext {kid}: path must name a .kext bundle")
        kexts[kid] = Kext(id=kid, **raw)

    return Manifest(path, owners, packages, kexts)

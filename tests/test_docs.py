"""Documentation consistency: relative links resolve and backlog IDs exist."""

import re

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
BACKLOG_REF = re.compile(r"\bB-\d{3}\b")


def markdown_files(root):
    files = [
        p
        for p in root.rglob("*.md")
        if not {".git", ".venv", "build", "dist", ".cache", ".pytest_cache"}
        & set(p.relative_to(root).parts)
    ]
    return sorted(files)


def test_relative_links_resolve(root):
    broken = []
    for md in markdown_files(root):
        for target in LINK.findall(md.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path = target.split("#", 1)[0]
            if path and not (md.parent / path).exists():
                broken.append(f"{md.relative_to(root)} -> {target}")
    assert broken == [], "\n".join(broken)


def test_backlog_references_are_defined(root):
    backlog = (root / "docs" / "backlog.md").read_text(encoding="utf-8")
    defined = set(re.findall(r"^### (B-\d{3})", backlog, re.M))
    used = set()
    for path in [*markdown_files(root), *root.glob("profiles/**/*"), *root.glob("hardware/**/*")]:
        if path.is_file():
            used |= set(BACKLOG_REF.findall(path.read_text(encoding="utf-8", errors="ignore")))
    assert used - defined == set(), f"undefined backlog IDs: {sorted(used - defined)}"


def test_required_documents_exist(root):
    for name in [
        "README.md",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "docs/installation.md",
        "docs/bios-settings.md",
        "docs/windows-linux.md",
        "docs/compatibility.md",
        "docs/hardware-inventory.md",
        "docs/graphics.md",
        "docs/troubleshooting.md",
        "docs/recovery.md",
        "docs/development.md",
        "docs/upstream-audit.md",
    ]:
        assert (root / name).is_file(), name

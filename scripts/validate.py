#!/usr/bin/env python3
"""Validate the research-ops package or an installed research repository."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote


LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def document_root_paths(config: str) -> list[str]:
    match = re.search(
        r"^document_roots:\s*\n(?P<body>(?:^[ \t]+.*(?:\n|$))*)",
        config,
        flags=re.MULTILINE,
    )
    if not match:
        return []
    return [value.strip('"\'') for value in re.findall(
        r"^\s+path:\s*(.+?)\s*$", match.group("body"), flags=re.MULTILINE
    )]


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def check(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def require_files(self, root: Path, paths: list[str]) -> None:
        for relative in paths:
            self.check((root / relative).is_file(), f"missing required file: {relative}")

    def check_markdown_links(self, root: Path, search_roots: list[Path] | None = None) -> None:
        sources: set[Path] = set()
        if search_roots is None:
            sources.update(root.rglob("*.md"))
        else:
            for search_root in search_roots:
                if search_root.is_file() and search_root.suffix.lower() == ".md":
                    sources.add(search_root)
                elif search_root.is_dir():
                    sources.update(search_root.rglob("*.md"))
        for source in sorted(sources):
            relative_source = source.relative_to(root)
            if relative_source.parts[:2] == (".research-ops", "templates"):
                continue
            text = source.read_text(encoding="utf-8")
            for match in LINK_RE.finditer(text):
                raw = match.group(1).strip().split()[0].strip("<>")
                if not raw or raw.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                path_part = unquote(raw.split("#", 1)[0])
                if not path_part or "<" in path_part or ">" in path_part:
                    continue
                target = (source.parent / path_part).resolve()
                self.check(
                    target.exists(),
                    f"broken Markdown link: {source.relative_to(root)} -> {path_part}",
                )

    def check_skill(self, path: Path) -> None:
        self.check(path.is_file(), f"missing skill: {path}")
        if not path.is_file():
            return
        text = path.read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(text)
        self.check(match is not None, f"skill has no YAML frontmatter: {path}")
        if match:
            frontmatter = match.group(1)
            self.check(re.search(r"^name:\s*\S+", frontmatter, re.MULTILINE) is not None,
                       f"skill has no name: {path}")
            self.check(re.search(r"^description:\s*\S+", frontmatter, re.MULTILINE) is not None,
                       f"skill has no description: {path}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_package(root: Path, validator: Validator) -> None:
    validator.require_files(root, [
        "README.md",
        "OPERATIONS.md",
        "VERSION",
        "CHANGELOG.md",
        "UPGRADING.md",
        "install.py",
        "research-ops.template.yml",
        "STATE.template/README.md",
        "STATE.template/decisions.md",
        "docs.template/README.md",
        "codex/INSTALL.md",
        "claude-code/INSTALL.md",
        "claude-code/CLAUDE.snippet.md",
    ])
    validator.check(not (root / "codex/prompts").exists(),
                    "deprecated codex/prompts directory must not exist")

    for adapter in ("codex", "claude-code"):
        for skill in ("docs-sync", "state-sync", "state-audit", "panel"):
            validator.check_skill(root / adapter / "skills" / skill / "SKILL.md")

    operations = read(root / "OPERATIONS.md")
    validator.check("last_state_sync_commit" in operations,
                    "OPERATIONS.md does not define a STATE SYNC commit cursor")
    validator.check("last_docs_sync_commit" in operations,
                    "OPERATIONS.md does not define a DOCS SYNC commit cursor")
    validator.check("## 6. 手続き: DOCS SYNC" in operations,
                    "OPERATIONS.md does not define the DOCS SYNC procedure")
    validator.check("## 7. 手続き: STATE SYNC" in operations,
                    "OPERATIONS.md does not define the STATE SYNC procedure")
    validator.check("research-ops.yml" in operations,
                    "OPERATIONS.md does not define activity-log discovery")
    validator.check("document_roots" in operations,
                    "OPERATIONS.md does not define multiple document roots")
    validator.check("既定はdry-run" in operations,
                    "OPERATIONS.md does not make SYNC dry-run by default")
    validator.check("人間が結論を承認" in operations,
                    "OPERATIONS.md does not gate decisions on human approval")
    validator.check(re.search(r"Claude|Codex|claude-code|codex/", operations) is None,
                    "tool-specific name leaked into tool-independent OPERATIONS.md")
    validator.check("/state-sync" not in operations,
                    "adapter-specific command leaked into tool-independent OPERATIONS.md")
    for ml_term in ("リーク", "ベースライン原理主義", "ターゲット変数", "CV分割"):
        validator.check(ml_term not in operations,
                        f"machine-learning-specific term leaked into OPERATIONS.md: {ml_term}")

    codex_install = read(root / "codex/INSTALL.md")
    validator.check(".agents/skills/" in codex_install,
                    "Codex install does not use repository skills")
    validator.check("~/.codex/prompts/" not in codex_install.split("## 旧版からの移行", 1)[0],
                    "Codex primary install still uses deprecated custom prompts")

    state_readme = read(root / "STATE.template/README.md")
    for key in (
        "last_state_sync_at", "last_state_sync_commit",
        "last_docs_sync_at", "last_docs_sync_commit", "activity_log_cursors",
    ):
        validator.check(key in state_readme, f"STATE README lacks cursor: {key}")

    for profile_name in (
        "general", "machine-learning", "experimental-science",
        "qualitative-research", "software-systems",
    ):
        profile_root = root / "profiles" / profile_name
        validator.require_files(root, [
            f"profiles/{profile_name}/profile.json",
            f"profiles/{profile_name}/PROFILE.md",
        ])
        if (profile_root / "profile.json").is_file():
            try:
                metadata = json.loads(read(profile_root / "profile.json"))
                validator.check(metadata.get("name") == profile_name,
                                f"profile name mismatch: {profile_name}")
            except json.JSONDecodeError as error:
                validator.errors.append(f"invalid profile JSON: {profile_name}: {error}")

    # Reproduce the documented minimal installation and validate its links.
    with tempfile.TemporaryDirectory(prefix="research-ops-validate-") as temp:
        target = Path(temp)
        (target / "STATE").mkdir()
        (target / "docs").mkdir()
        shutil.copy2(root / "OPERATIONS.md", target / "OPERATIONS.md")
        shutil.copy2(root / "research-ops.template.yml", target / "research-ops.yml")
        shutil.copy2(root / "profiles/general/PROFILE.md", target / "RESEARCH_PROFILE.md")
        shutil.copy2(root / "STATE.template/README.md", target / "STATE/README.md")
        shutil.copy2(root / "STATE.template/decisions.md", target / "STATE/decisions.md")
        shutil.copy2(root / "docs.template/README.md", target / "docs/README.md")
        installed_readme = target / "STATE/README.md"
        installed_readme.write_text(
            read(installed_readme).replace("<プロジェクト名>", "validation-sample"),
            encoding="utf-8",
        )
        validate_installed(target, validator, base_ref=None)


def validate_installed(root: Path, validator: Validator, base_ref: str | None) -> None:
    validator.require_files(root, [
        "OPERATIONS.md",
        "RESEARCH_PROFILE.md",
        "research-ops.yml",
        "STATE/README.md",
        "STATE/decisions.md",
        "docs/README.md",
    ])
    if (root / "STATE/README.md").is_file():
        state_readme = read(root / "STATE/README.md")
        for key in (
            "last_state_sync_at", "last_state_sync_commit",
            "last_docs_sync_at", "last_docs_sync_commit", "activity_log_cursors",
        ):
            validator.check(key in state_readme, f"STATE/README.md lacks cursor: {key}")
        validator.check("<プロジェクト名>" not in state_readme,
                        "STATE/README.md still contains the project-name placeholder")

    registered_document_paths: list[Path] = []
    config = root / "research-ops.yml"
    if config.is_file():
        config_text = read(config)
        validator.check(re.search(r"^version:\s*1\s*$", config_text, re.MULTILINE) is not None,
                        "research-ops.yml must declare version: 1")
        validator.check(re.search(r"^profile:\s*\S+\s*$", config_text, re.MULTILINE) is not None,
                        "research-ops.yml must declare profile")
        registered_documents = document_root_paths(config_text)
        validator.check(bool(registered_documents),
                        "research-ops.yml must declare at least one document root")
        validator.check(len(registered_documents) == len(set(registered_documents)),
                        "research-ops.yml contains duplicate document-root paths")
        for registered_path in registered_documents:
            path = Path(registered_path)
            validator.check(not path.is_absolute(),
                            f"document root must be relative: {registered_path}")
            if not path.is_absolute():
                resolved = (root / path).resolve()
                try:
                    resolved.relative_to(root.resolve())
                    inside_root = True
                except ValueError:
                    inside_root = False
                validator.check(inside_root,
                                f"document root escapes repository: {registered_path}")
                validator.check(resolved.exists(),
                                f"registered document root does not exist: {registered_path}")
                if inside_root and resolved.exists():
                    registered_document_paths.append(resolved)
        validator.check(re.search(r"^activity_logs:\s*(\[\])?\s*$", config_text, re.MULTILINE) is not None,
                        "research-ops.yml must declare activity_logs")

    if base_ref and (root / "STATE/decisions.md").is_file():
        result = subprocess.run(
            ["git", "show", f"{base_ref}:STATE/decisions.md"],
            cwd=root,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        validator.check(result.returncode == 0,
                        f"could not read STATE/decisions.md at {base_ref}: {result.stderr.strip()}")
        if result.returncode == 0:
            current = read(root / "STATE/decisions.md")
            validator.check(current.startswith(result.stdout),
                            "STATE/decisions.md changed before its previous end; it must be append-only")

    validator.check_markdown_links(
        root,
        [root / "STATE", root / "RESEARCH_PROFILE.md", *registered_document_paths],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path,
                        help="Validate an installed research repository instead of this package")
    parser.add_argument("--base-ref",
                        help="Git ref used to enforce append-only STATE/decisions.md")
    args = parser.parse_args()

    root = (args.target or Path(__file__).resolve().parents[1]).resolve()
    validator = Validator()
    if args.target:
        validate_installed(root, validator, args.base_ref)
    else:
        validate_package(root, validator)
        validator.check_markdown_links(root)

    if validator.errors:
        print(f"validation failed with {len(validator.errors)} error(s):", file=sys.stderr)
        for error in validator.errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"validation passed: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

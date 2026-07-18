#!/usr/bin/env python3
"""Install research-ops interactively or from command-line arguments."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = Path(".research-ops/installation.json")
BEGIN_MARKER = "<!-- research-ops:begin -->"
END_MARKER = "<!-- research-ops:end -->"


@dataclass(frozen=True)
class Profile:
    name: str
    display_name: str
    description: str
    root: Path


@dataclass
class Action:
    path: Path
    content: str
    kind: str = "managed"
    status: str = "pending"
    backup: bool = False


def parse_document_roots(config: str | None) -> list[dict[str, str]]:
    if not config:
        return []
    match = re.search(
        r"^document_roots:\s*\n(?P<body>(?:^[ \t]+.*(?:\n|$))*)",
        config,
        flags=re.MULTILINE,
    )
    if not match:
        return []
    roots: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in match.group("body").splitlines():
        item = re.match(r"^\s*-\s+id:\s*(.+?)\s*$", line)
        field = re.match(r"^\s+(path|scope|include):\s*(.+?)\s*$", line)
        if item:
            if current:
                roots.append(current)
            current = {"id": item.group(1).strip('"\'')}
        elif field and current is not None:
            current[field.group(1)] = field.group(2).strip('"\'')
    if current:
        roots.append(current)
    return roots


def root_id(path: str, used: set[str]) -> str:
    candidate = re.sub(r"[^\w-]+", "-", Path(path).name, flags=re.UNICODE).strip("-").lower()
    candidate = candidate or "documents"
    base = candidate
    index = 2
    while candidate in used:
        candidate = f"{base}-{index}"
        index += 1
    used.add(candidate)
    return candidate


def merge_document_roots(existing: list[dict[str, str]], additions: list[str]) -> list[dict[str, str]]:
    roots = [dict(root) for root in existing] or [{
        "id": "shared", "path": "docs", "scope": "project", "include": "**/*.md"
    }]
    known_paths = {root.get("path", "").replace("\\", "/").rstrip("/") for root in roots}
    used_ids = {root.get("id", "") for root in roots}
    for path in additions:
        normalized = path.replace("\\", "/").rstrip("/")
        if normalized in known_paths:
            continue
        identifier = root_id(normalized, used_ids)
        roots.append({
            "id": identifier,
            "path": normalized,
            "scope": identifier,
            "include": "**/*.md",
        })
        known_paths.add(normalized)
    return roots


def render_document_roots(roots: list[dict[str, str]]) -> str:
    lines = ["document_roots:"]
    for root in roots:
        lines.extend([
            f"  - id: {json.dumps(root['id'], ensure_ascii=False)}",
            f"    path: {json.dumps(root['path'], ensure_ascii=False)}",
            f"    scope: {json.dumps(root.get('scope', root['id']), ensure_ascii=False)}",
            f"    include: {json.dumps(root.get('include', '**/*.md'), ensure_ascii=False)}",
        ])
    return "\n".join(lines)


def replace_yaml_block(text: str, key: str, replacement: str) -> str:
    pattern = re.compile(
        rf"^{re.escape(key)}:\s*\n(?:^[ \t]+.*(?:\n|$))*",
        flags=re.MULTILINE,
    )
    match = pattern.search(text)
    if match:
        return text[:match.start()] + replacement + "\n" + text[match.end():]
    anchor = re.search(r"^activity_logs:", text, flags=re.MULTILINE)
    if anchor:
        return text[:anchor.start()] + replacement + "\n\n" + text[anchor.start():]
    return text.rstrip() + "\n\n" + replacement + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def discover_profiles() -> dict[str, Profile]:
    profiles: dict[str, Profile] = {}
    for metadata_path in sorted((ROOT / "profiles").glob("*/profile.json")):
        data = json.loads(read_text(metadata_path))
        profile = Profile(
            name=data["name"],
            display_name=data["display_name"],
            description=data["description"],
            root=metadata_path.parent,
        )
        profiles[profile.name] = profile
    if "general" not in profiles:
        raise RuntimeError("profiles/general/profile.json is required")
    return dict(sorted(
        profiles.items(),
        key=lambda item: (item[0] != "general", item[1].display_name),
    ))


def load_manifest(target: Path) -> dict:
    path = target / MANIFEST_PATH
    if not path.is_file():
        return {}
    try:
        return json.loads(read_text(path))
    except (json.JSONDecodeError, OSError) as error:
        raise RuntimeError(f"cannot read {MANIFEST_PATH}: {error}") from error


def choose(prompt: str, options: list[tuple[str, str]], default: str | None = None) -> str:
    print(f"\n{prompt}")
    for index, (value, label) in enumerate(options, 1):
        suffix = " [現在]" if value == default else ""
        print(f"  {index}. {label}{suffix}")
    while True:
        answer = input("> ").strip()
        if not answer and default is not None:
            return default
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1][0]
        values = {value for value, _ in options}
        if answer in values:
            return answer
        print("番号または選択肢の名前を入力してください。")


def confirm(prompt: str) -> bool:
    return input(f"{prompt} [y/N]: ").strip().lower() in {"y", "yes"}


def render_config(existing: str | None, version: str, profile: str,
                  document_roots: list[dict[str, str]]) -> str:
    if existing is None:
        template = read_text(ROOT / "research-ops.template.yml")
        text = re.sub(r'^package_version:\s*.*$', f'package_version: "{version}"', template,
                      flags=re.MULTILINE).replace("profile: general", f"profile: {profile}")
        return replace_yaml_block(text, "document_roots", render_document_roots(document_roots))

    text = existing
    text = re.sub(r"^experiment_logs:", "activity_logs:", text, flags=re.MULTILINE)
    if re.search(r"^package_version:", text, re.MULTILINE):
        text = re.sub(r'^package_version:\s*.*$', f'package_version: "{version}"', text,
                      flags=re.MULTILINE)
    else:
        version_match = re.search(r"^version:\s*.*$", text, re.MULTILINE)
        insertion = f'package_version: "{version}"'
        if version_match:
            text = text[:version_match.end()] + "\n" + insertion + text[version_match.end():]
        else:
            text = "version: 1\n" + insertion + "\n" + text
    if re.search(r"^profile:", text, re.MULTILINE):
        text = re.sub(r"^profile:\s*.*$", f"profile: {profile}", text, flags=re.MULTILINE)
    else:
        package_match = re.search(r"^package_version:\s*.*$", text, re.MULTILINE)
        assert package_match
        text = text[:package_match.end()] + f"\nprofile: {profile}" + text[package_match.end():]
    if not text.endswith("\n"):
        text += "\n"
    return replace_yaml_block(text, "document_roots", render_document_roots(document_roots))


def migrate_state_readme(text: str) -> str:
    migrated = re.sub(r"^last_sync_at:", "last_state_sync_at:", text, flags=re.MULTILINE)
    migrated = re.sub(r"^last_sync_commit:", "last_state_sync_commit:", migrated,
                      flags=re.MULTILINE)
    migrated = re.sub(r"^experiment_log_cursors:", "activity_log_cursors:", migrated,
                      flags=re.MULTILINE)
    required = {
        "last_state_sync_at": '""',
        "last_state_sync_commit": '""',
        "last_docs_sync_at": '""',
        "last_docs_sync_commit": '""',
        "activity_log_cursors": "{}",
    }
    frontmatter = re.match(r"\A---\s*\n(?P<body>.*?)\n---\s*\n", migrated, flags=re.DOTALL)
    if not frontmatter:
        header = "---\n" + "\n".join(f"{key}: {value}" for key, value in required.items()) + "\n---\n\n"
        return header + migrated.lstrip()
    body = frontmatter.group("body")
    missing_lines = [f"{key}: {value}" for key, value in required.items()
                     if not re.search(rf"^{re.escape(key)}:", body, flags=re.MULTILINE)]
    if not missing_lines:
        return migrated
    new_body = body.rstrip() + "\n" + "\n".join(missing_lines)
    return migrated[:frontmatter.start("body")] + new_body + migrated[frontmatter.end("body"):]


def managed_block(body: str) -> str:
    return f"{BEGIN_MARKER}\n{body.strip()}\n{END_MARKER}"


def merge_block(existing: str | None, body: str) -> str:
    block = managed_block(body)
    if existing is None or not existing.strip():
        return block + "\n"
    pattern = re.compile(re.escape(BEGIN_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL)
    if pattern.search(existing):
        result = pattern.sub(block, existing, count=1)
    else:
        result = existing.rstrip() + "\n\n" + block + "\n"
    return result if result.endswith("\n") else result + "\n"


def add_tree(actions: list[Action], source: Path, destination: Path) -> None:
    if not source.exists():
        return
    for path in sorted(source.rglob("*")):
        if path.is_file():
            relative = path.relative_to(source)
            actions.append(Action(destination / relative, read_text(path)))


def build_actions(target: Path, adapters: list[str], profile: Profile,
                  version: str, document_roots: list[dict[str, str]]) -> list[Action]:
    actions: list[Action] = [
        Action(Path("OPERATIONS.md"), read_text(ROOT / "OPERATIONS.md")),
        Action(Path("RESEARCH_PROFILE.md"), read_text(profile.root / "PROFILE.md")),
    ]

    config_path = target / "research-ops.yml"
    existing_config = read_text(config_path) if config_path.is_file() else None
    actions.append(Action(Path("research-ops.yml"),
                          render_config(existing_config, version, profile.name, document_roots),
                          kind="schema"))

    state_readme_path = target / "STATE/README.md"
    if state_readme_path.is_file():
        migrated = migrate_state_readme(read_text(state_readme_path))
        actions.append(Action(Path("STATE/README.md"), migrated, kind="schema"))
    else:
        state_readme = read_text(ROOT / "STATE.template/README.md").replace(
            "<プロジェクト名>", target.name
        )
        actions.append(Action(Path("STATE/README.md"), state_readme, kind="protected"))

    actions.extend([
        Action(Path("STATE/decisions.md"), read_text(ROOT / "STATE.template/decisions.md"),
               kind="protected"),
        Action(Path("docs/README.md"), read_text(ROOT / "docs.template/README.md"),
               kind="protected"),
        Action(Path(".research-ops/VERSION"), version + "\n"),
        Action(Path(".research-ops/validate.py"), read_text(ROOT / "scripts/validate.py")),
    ])

    optional_core = ROOT / "STATE.template"
    for path in sorted(optional_core.glob("*.md")):
        if path.name not in {"README.md", "decisions.md"}:
            actions.append(Action(Path(".research-ops/templates/core/STATE") / path.name,
                                  read_text(path)))
    add_tree(actions, profile.root / "STATE",
             Path(".research-ops/templates/profiles") / profile.name / "STATE")

    if "codex" in adapters:
        add_tree(actions, ROOT / "codex/skills", Path(".agents/skills"))
        snippet = read_text(ROOT / "codex/AGENTS.snippet.md")
        agents_path = target / "AGENTS.md"
        existing = read_text(agents_path) if agents_path.is_file() else None
        actions.append(Action(Path("AGENTS.md"), merge_block(existing, snippet), kind="schema"))

    if "claude-code" in adapters:
        add_tree(actions, ROOT / "claude-code/skills", Path(".claude/skills"))
        snippet = read_text(ROOT / "claude-code/CLAUDE.snippet.md")
        claude_path = target / "CLAUDE.md"
        existing = read_text(claude_path) if claude_path.is_file() else None
        actions.append(Action(Path("CLAUDE.md"), merge_block(existing, snippet), kind="schema"))

    return actions


def classify_actions(target: Path, actions: list[Action], manifest: dict,
                     conflict_mode: str, interactive: bool) -> None:
    previous_hashes = manifest.get("files", {})
    for action in actions:
        destination = target / action.path
        if not destination.exists():
            action.status = "create"
            continue
        current = read_text(destination)
        if current == action.content:
            action.status = "unchanged"
            continue
        if action.kind == "protected":
            action.status = "skip-protected"
            continue
        if action.kind == "schema":
            action.status = "update"
            continue
        previous_hash = previous_hashes.get(action.path.as_posix())
        if previous_hash and sha256_text(current) == previous_hash:
            action.status = "update"
            continue

        mode = conflict_mode
        if mode == "ask" and interactive:
            mode = choose(
                f"{action.path} は導入後に変更されています。",
                [("skip", "スキップ"), ("backup", "バックアップして更新"),
                 ("overwrite", "上書き")],
                default="skip",
            )
        elif mode == "ask":
            mode = "skip"
        if mode == "skip":
            action.status = "skip-conflict"
        else:
            action.status = "update"
            action.backup = mode == "backup"


def display_plan(target: Path, profile: Profile, adapters: list[str],
                 document_roots: list[dict[str, str]], actions: list[Action]) -> None:
    print("\n導入計画")
    print(f"  導入先: {target}")
    print(f"  プロファイル: {profile.display_name} ({profile.name})")
    print(f"  導入・更新する実行環境: {', '.join(adapters) if adapters else 'なし'}")
    print("  文書ルート:")
    for root in document_roots:
        print(f"    - {root['path']} ({root.get('scope', root['id'])})")
    labels = {
        "create": "+",
        "update": "~",
        "unchanged": "=",
        "skip-protected": "!",
        "skip-conflict": "!",
    }
    for action in actions:
        print(f"  {labels.get(action.status, '?')} {action.path} [{action.status}]")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n",
                                     dir=path.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def apply_actions(target: Path, actions: list[Action], version: str,
                  profile: Profile, adapters: list[str]) -> None:
    timestamp = dt.datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
    backup_root = target / ".research-ops/backups" / timestamp
    for action in actions:
        if action.status not in {"create", "update"}:
            continue
        destination = target / action.path
        if action.backup and destination.exists():
            backup = backup_root / action.path
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, backup)
        atomic_write(destination, action.content)

    managed_hashes: dict[str, str] = {}
    for action in actions:
        destination = target / action.path
        if action.kind == "managed" and destination.is_file() and action.status not in {
            "skip-conflict", "skip-protected"
        }:
            managed_hashes[action.path.as_posix()] = sha256_text(read_text(destination))
    manifest = {
        "package_version": version,
        "profile": profile.name,
        "adapters": adapters,
        "installed_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "files": managed_hashes,
    }
    atomic_write(target / MANIFEST_PATH, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def parse_args(profiles: dict[str, Profile]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install research-ops into a research repository")
    parser.add_argument("--target", type=Path)
    parser.add_argument("--adapter", choices=["codex", "claude-code", "both", "none"])
    parser.add_argument("--profile", choices=sorted(profiles))
    parser.add_argument("--document-root", action="append", default=[], metavar="PATH",
                        help="Add a document directory or file; may be repeated")
    parser.add_argument("--conflict", choices=["ask", "skip", "backup", "overwrite"])
    parser.add_argument("--yes", action="store_true", help="Apply without final confirmation")
    parser.add_argument("--dry-run", action="store_true", help="Show the plan without writing files")
    parser.add_argument("--list-profiles", action="store_true")
    return parser.parse_args()


def main() -> int:
    profiles = discover_profiles()
    args = parse_args(profiles)
    if args.list_profiles:
        for profile in profiles.values():
            print(f"{profile.name}\t{profile.display_name}\t{profile.description}")
        return 0

    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if args.target is None:
        if not interactive:
            print("--target is required in non-interactive mode", file=sys.stderr)
            return 2
        print("research-ops installer")
        entered = input("\n導入先の研究リポジトリ: ").strip().strip('"')
        if not entered:
            print("導入先は必須です。", file=sys.stderr)
            return 2
        args.target = Path(entered)

    target = args.target.expanduser().resolve()
    if target == ROOT:
        print("research-ops自身を導入先には指定できません。", file=sys.stderr)
        return 2
    if not target.exists():
        if interactive and confirm(f"{target} を作成しますか?"):
            target.mkdir(parents=True)
        else:
            print(f"target does not exist: {target}", file=sys.stderr)
            return 2
    if not target.is_dir():
        print(f"target is not a directory: {target}", file=sys.stderr)
        return 2

    try:
        previous = load_manifest(target)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 2

    default_adapter = args.adapter or (
        "both" if set(previous.get("adapters", [])) == {"codex", "claude-code"}
        else (previous.get("adapters") or [None])[0]
    )
    if args.adapter is None:
        if not interactive:
            print("--adapter is required in non-interactive mode", file=sys.stderr)
            return 2
        args.adapter = choose(
            "利用する実行環境:",
            [("codex", "Codex"), ("claude-code", "Claude Code"),
             ("both", "両方"), ("none", "アダプタなし")],
            default=default_adapter if default_adapter in {"codex", "claude-code", "both", "none"} else None,
        )

    default_profile = previous.get("profile", "general")
    if args.profile is None:
        if not interactive:
            print("--profile is required in non-interactive mode", file=sys.stderr)
            return 2
        args.profile = choose(
            "研究プロファイル:",
            [(profile.name, f"{profile.display_name}: {profile.description}")
             for profile in profiles.values()],
            default=default_profile if default_profile in profiles else "general",
        )

    existing_config_path = target / "research-ops.yml"
    existing_config = read_text(existing_config_path) if existing_config_path.is_file() else None
    existing_document_roots = parse_document_roots(existing_config)
    additions = list(args.document_root)
    if interactive and not args.document_root:
        current = existing_document_roots or [{"path": "docs", "scope": "project"}]
        print("\n現在の文書ルート:")
        for root in current:
            print(f"  - {root['path']} ({root.get('scope', root.get('id', 'project'))})")
        print("追加する文書フォルダまたはファイルを入力してください。空欄で終了します。")
        while True:
            value = input("> ").strip().strip('"')
            if not value:
                break
            additions.append(value)

    normalized_additions: list[str] = []
    for value in additions:
        candidate = Path(value)
        if candidate.is_absolute():
            print(f"document root must be relative to the target repository: {value}", file=sys.stderr)
            return 2
        resolved = (target / candidate).resolve()
        try:
            relative = resolved.relative_to(target)
        except ValueError:
            print(f"document root escapes the target repository: {value}", file=sys.stderr)
            return 2
        if relative.as_posix() != "docs" and not resolved.exists():
            print(f"document root does not exist: {value}", file=sys.stderr)
            return 2
        normalized_additions.append(relative.as_posix())
    document_roots = merge_document_roots(existing_document_roots, normalized_additions)

    adapters = {
        "codex": ["codex"],
        "claude-code": ["claude-code"],
        "both": ["codex", "claude-code"],
        "none": [],
    }[args.adapter]
    version = read_text(ROOT / "VERSION").strip()
    profile = profiles[args.profile]
    conflict_mode = args.conflict or ("ask" if interactive and not args.yes else "skip")
    actions = build_actions(target, adapters, profile, version, document_roots)
    classify_actions(target, actions, previous, conflict_mode, interactive)
    display_plan(target, profile, adapters, document_roots, actions)

    if args.dry_run:
        print("\ndry-runのため変更していません。")
        return 0
    if not args.yes:
        if not interactive:
            print("use --yes to apply in non-interactive mode", file=sys.stderr)
            return 2
        if not confirm("この内容で実行しますか?"):
            print("中止しました。")
            return 0

    effective_adapters = sorted(set(previous.get("adapters", [])) | set(adapters))
    apply_actions(target, actions, version, profile, effective_adapters)
    changed = sum(action.status in {"create", "update"} for action in actions)
    skipped = sum(action.status.startswith("skip") for action in actions)
    print(f"\n完了: {changed}件を作成・更新、{skipped}件をスキップしました。")
    print(f"検証: python {target / '.research-ops/validate.py'} --target {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

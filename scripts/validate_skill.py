#!/usr/bin/env python3
"""Validate the academic-fraud-detector skill structure.

This is intentionally dependency-free so contributors can run it in a fresh
checkout before publishing skill edits.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED_SKILL_SECTIONS = [
    "# 耿同学 Skill：学术诚信初筛",
    "## 工作原则",
    "## 证据等级",
    "## 分析流程",
    "## 报告模板",
    "## 安全边界",
]

REQUIRED_REPORT_PHRASES = [
    "结论等级：G3 外部确认问题",
    "可能的无害解释",
    "免责声明",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        fail("SKILL.md must start with YAML frontmatter")

    end = text.find("\n---\n", 4)
    if end == -1:
        fail("SKILL.md frontmatter must close with ---")

    raw = text[4:end]
    body = text[end + 5 :]
    data: dict[str, str] = {}

    for line in raw.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)", line)
        if not match:
            fail(f"Unsupported frontmatter line: {line}")
        key, value = match.groups()
        data[key] = value.strip().strip('"')

    return data, body


def validate_skill(root: Path) -> None:
    skill_path = root / "SKILL.md"
    if not skill_path.exists():
        fail("Missing SKILL.md")

    frontmatter, body = parse_frontmatter(skill_path.read_text(encoding="utf-8"))
    if set(frontmatter) != {"name", "description"}:
        fail("SKILL.md frontmatter must contain only name and description")
    if frontmatter["name"] != "geng-academic-fraud-detector":
        fail("Unexpected skill name")
    if len(frontmatter["description"]) < 80:
        fail("Description is too short to guide skill triggering")
    if not re.fullmatch(r"[a-z0-9-]+", frontmatter["name"]):
        fail("Skill name must be lowercase letters, digits, and hyphens")

    for section in REQUIRED_SKILL_SECTIONS:
        if section not in body:
            fail(f"Missing required section in SKILL.md: {section}")

    if "不要把 AI 自行发现的线索写成“实锤”" not in body:
        fail("SKILL.md must explicitly guard against overclaiming AI findings")
    if "无法判断" not in body:
        fail("SKILL.md must require uncertainty reporting")


def validate_readme_links(root: Path) -> None:
    readme_path = root / "README.md"
    if not readme_path.exists():
        fail("Missing README.md")

    text = readme_path.read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    for link in links:
        if re.match(r"^(https?|mailto):", link):
            continue
        local = link.split("#", 1)[0]
        if local and not (root / local).exists():
            fail(f"README.md links to missing path: {link}")


def validate_openai_yaml(root: Path) -> None:
    openai_yaml = root / "agents" / "openai.yaml"
    if not openai_yaml.exists():
        fail("Missing agents/openai.yaml")

    text = openai_yaml.read_text(encoding="utf-8")
    for field in ("display_name", "short_description", "default_prompt"):
        if f"{field}:" not in text:
            fail(f"agents/openai.yaml missing interface field: {field}")
    if "$geng-academic-fraud-detector" not in text:
        fail("agents/openai.yaml default_prompt must mention $geng-academic-fraud-detector")


def validate_example(root: Path) -> None:
    example_path = root / "test" / "example-report.md"
    if not example_path.exists():
        fail("Missing test/example-report.md")

    text = example_path.read_text(encoding="utf-8")
    for phrase in REQUIRED_REPORT_PHRASES:
        if phrase not in text:
            fail(f"Example report missing phrase: {phrase}")

    if re.search(r"综合评定[:：].*实锤", text):
        fail("Example report should not use unsafe AI overclaim labels")


def main() -> None:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    validate_skill(root)
    validate_readme_links(root)
    validate_openai_yaml(root)
    validate_example(root)
    print("OK: skill structure validated")


if __name__ == "__main__":
    main()

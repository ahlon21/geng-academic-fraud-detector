#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SkillOpt 式行为验证门 —— rule-based judge（无需 LLM 评委）。

借鉴 microsoft/SkillOpt 的 "rule judge" 设计：把"一份合格的打假报告应满足什么"
拆成一组**确定性、可复现**的检查，对 rollout（技能实际产出的报告 Markdown）打分。
hard=1.0 当且仅当所有检查通过；soft=通过比例。这样技能改动是否进步可被客观度量，
而不是凭感觉——这正是 SkillOpt 的"validation gate"。

与本 repo 既有的**静态**校验器（validate_skill.py / skill_gate.py，检查文档结构）互补：
本 judge 检查**技能的行为产出**。

检查类型（check kinds）：
  contains_any   : 文中包含任一给定串（大小写不敏感）→ 通过
  contains_all   : 文中包含全部给定串 → 通过
  not_contains   : 文中不含任何给定串 → 通过（防过度断言/假阳性）
  regex          : 命中正则 → 通过
  section_present: 含给定小节标题 → 通过
  verdict_in     : 解析"综合评定"行的等级，∈ 允许集合 → 通过

用法：
  python3 eval/judge.py score   --case eval/cases/<x>.json --report report.md
  python3 eval/judge.py oracle  --case eval/cases/<x>.json [--repo <dir>]
  python3 eval/judge.py selftest
"""
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)


# --------------------------------------------------------------------------- #
def _norm(s):
    return (s or "").lower()


def _verdict_level(text):
    """从报告里抽取'综合评定'等级（emoji 或词），返回规范化标签集合。"""
    m = re.search(r"综合评定[:：]\s*([^\n]+)", text)
    seg = m.group(1) if m else text[:200]
    labels = set()
    for emo, lab in [("🔴", "red"), ("🟠", "orange"), ("🟡", "yellow"), ("✅", "clean")]:
        if emo in seg:
            labels.add(lab)
    for word, lab in [("实锤", "red"), ("高度可疑", "orange"), ("存疑", "yellow"),
                      ("清白", "clean"), ("无异常", "clean")]:
        if word in seg:
            labels.add(lab)
    return labels


def run_check(chk, text):
    kind = chk["kind"]
    low = _norm(text)
    if kind == "contains_any":
        return any(_norm(v) in low for v in chk["values"])
    if kind == "contains_all":
        return all(_norm(v) in low for v in chk["values"])
    if kind == "not_contains":
        return not any(_norm(v) in low for v in chk["values"])
    if kind == "regex":
        return re.search(chk["pattern"], text, re.M | re.S) is not None
    if kind == "section_present":
        return _norm(chk["value"]) in low
    if kind == "verdict_in":
        return bool(_verdict_level(text) & set(chk["allowed"]))
    raise ValueError(f"未知检查类型: {kind}")


def score_report(case, text):
    checks = case.get("checks", [])
    results = []
    total_w = 0.0
    got_w = 0.0
    for chk in checks:
        w = float(chk.get("weight", 1.0))
        ok = run_check(chk, text)
        total_w += w
        if ok:
            got_w += w
        results.append((ok, chk.get("desc", chk["kind"]), w))
    soft = got_w / total_w if total_w else 1.0
    # hard = all *actionable* (weight>0) checks pass; weight-0 checks are
    # informational only and must not drag the hard score.
    hard = 1.0 if all(ok for ok, _, w in results if w > 0) else 0.0
    return hard, soft, results


# --------------------------------------------------------------------------- #
def cmd_score(args):
    case = json.load(open(args.case, encoding="utf-8"))
    text = open(args.report, encoding="utf-8", errors="replace").read()
    hard, soft, results = score_report(case, text)
    print(f"案例 {case['id']}：hard={hard:.0f}  soft={soft:.2f}")
    for ok, desc, w in results:
        print(f"  {'✅' if ok else '❌'} [{w:g}] {desc}")
    return 0 if hard == 1.0 else 1


def cmd_oracle(args):
    """运行案例自带的 tool_oracle：客观验证工具箱对该案例的判定（不依赖 LLM）。"""
    case = json.load(open(args.case, encoding="utf-8"))
    repo = args.repo or REPO
    oracles = case.get("tool_oracle", [])
    if not oracles:
        print(f"案例 {case['id']}：无 tool_oracle，跳过。")
        return 0
    ok_all = True
    print(f"案例 {case['id']} 的工具预言（tool oracle）：")
    for orc in oracles:
        cmd = [a.replace("{REPO}", repo).replace("{CASE_DIR}", os.path.join(ROOT, "cases"))
               for a in orc["cmd"]]
        expect = orc.get("expect_exit", 0)
        try:
            r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=60)
            got = r.returncode
        except Exception as exc:  # noqa
            print(f"  ❌ {orc.get('desc','')}: 运行失败 {exc}")
            ok_all = False
            continue
        ok = got == expect
        ok_all = ok_all and ok
        print(f"  {'✅' if ok else '❌'} {orc.get('desc','')}  (期望退出码 {expect}, 实际 {got})")
    return 0 if ok_all else 1


# --------------------------------------------------------------------------- #
_SELFTEST_REPORT_GOOD = """
# 🔍 打假报告
## 综合评定：🔴 实锤
### 发现 1：数据造假
- 位置：Table 2 第 3 行
- 证据：GRIMMER 不一致，可复现命令 `python3 scripts/forensics.py grimmer --mean 3.45 --sd 1.12 --n 20`
六式覆盖表 ... PubPeer ... appears ...
"""
_SELFTEST_REPORT_BAD = """
# 报告
## 综合评定：✅ 清白
看起来没问题，没有运行任何脚本。
"""


def cmd_selftest(args):
    case = {
        "id": "selftest",
        "checks": [
            {"kind": "verdict_in", "allowed": ["red", "orange"], "desc": "判为红/橙"},
            {"kind": "contains_any", "values": ["forensics.py", "grimmer"], "desc": "引用可复现命令"},
            {"kind": "not_contains", "values": ["清白", "✅"], "desc": "未误判清白"},
            {"kind": "section_present", "value": "综合评定", "desc": "含综合评定"},
        ],
    }
    hg, sg, _ = score_report(case, _SELFTEST_REPORT_GOOD)
    hb, sb, _ = score_report(case, _SELFTEST_REPORT_BAD)
    ok = (hg == 1.0 and sg == 1.0 and hb == 0.0 and sb < 1.0)
    print(f"good: hard={hg} soft={sg:.2f} | bad: hard={hb} soft={sb:.2f}")
    print("✅ judge 自检通过" if ok else "❌ judge 自检失败")
    return 0 if ok else 1


def build_parser():
    p = argparse.ArgumentParser(description="SkillOpt 式行为验证门 (rule judge)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score", help="对一份报告 Markdown 按案例打分")
    s.add_argument("--case", required=True)
    s.add_argument("--report", required=True)
    s.set_defaults(func=cmd_score)
    o = sub.add_parser("oracle", help="运行案例的工具预言（客观）")
    o.add_argument("--case", required=True)
    o.add_argument("--repo")
    o.set_defaults(func=cmd_oracle)
    t = sub.add_parser("selftest", help="judge 自检")
    t.set_defaults(func=cmd_selftest)
    return p


if __name__ == "__main__":
    a = build_parser().parse_args()
    sys.exit(a.func(a))

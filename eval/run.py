#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SkillOpt 式行为验证门 —— 批量运行器。

两种用途：
  1) oracles  —— 运行所有案例的 tool_oracle（客观、无 LLM）：确认取证工具箱对每个
     held-out 案例的判定与 ground truth 一致。这是可随时运行的回归门。
  2) grade    —— 给定一个报告目录（每个案例一份 <case_id>.md），按 rule judge 打分，
     输出 hard/soft 计分板与均值。用于对比 baseline vs candidate 技能的 rollout。

用法：
  python3 eval/run.py oracles
  python3 eval/run.py grade --reports <dir>            # 文件名须为 <case_id>.md
  python3 eval/run.py grade --reports <dir> --label baseline
"""
import argparse
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
import judge  # noqa: E402


def load_cases():
    return sorted(glob.glob(os.path.join(ROOT, "cases", "*.json")))


def cmd_oracles(args):
    print("══ Tool oracles（客观验证：工具箱对 held-out 案例的判定）══")
    all_ok = True
    for cf in load_cases():
        case = json.load(open(cf, encoding="utf-8"))

        class _A:
            pass
        a = _A(); a.case = cf; a.repo = REPO
        rc = judge.cmd_oracle(a)
        all_ok = all_ok and rc == 0
    print("─" * 56)
    print("✅ 所有 tool oracle 通过" if all_ok else "❌ 存在未通过的 oracle")
    return 0 if all_ok else 1


def cmd_grade(args):
    cases = load_cases()
    print(f"══ Rule-judge 计分板  [{args.label or os.path.basename(args.reports)}] ══")
    hards, softs = [], []
    for cf in cases:
        case = json.load(open(cf, encoding="utf-8"))
        rpt = os.path.join(args.reports, f"{case['id']}.md")
        if not os.path.exists(rpt):
            print(f"  ⚠ 缺少报告 {case['id']}.md → 记 0 分")
            hards.append(0.0); softs.append(0.0)
            continue
        text = open(rpt, encoding="utf-8", errors="replace").read()
        hard, soft, results = judge.score_report(case, text)
        hards.append(hard); softs.append(soft)
        print(f"  {case['id']:<18} hard={hard:.0f}  soft={soft:.2f}")
        for ok, desc, w in results:
            if not ok:
                print(f"        ❌ [{w:g}] {desc}")
    n = len(cases) or 1
    mh, ms = sum(hards) / n, sum(softs) / n
    print("─" * 56)
    print(f"  均值  hard={mh:.2f}  soft={ms:.2f}   ({len(cases)} 案例)")
    return 0


def build_parser():
    p = argparse.ArgumentParser(description="SkillOpt 式行为验证门 批量运行器")
    sub = p.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("oracles", help="运行所有案例的 tool oracle（客观回归门）")
    o.set_defaults(func=cmd_oracles)
    g = sub.add_parser("grade", help="对报告目录按 rule judge 打分")
    g.add_argument("--reports", required=True, help="报告目录，文件名 <case_id>.md")
    g.add_argument("--label", default="")
    g.set_defaults(func=cmd_grade)
    return p


if __name__ == "__main__":
    a = build_parser().parse_args()
    sys.exit(a.func(a))

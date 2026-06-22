#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
耿同学打假工具箱 — 统计与文本取证 CLI
geng-forensics: statistical & text forensics for academic-integrity screening.

纯标准库实现，无需安装任何第三方包 (Python 3.8+)。
Pure standard library, no third-party dependencies (Python 3.8+).

子命令 / sub-commands:
    grim       GRIM test — 检验报告的"均值"对整数型数据在数学上是否可能
    grimmer    GRIMMER test — 检验"均值+标准差"组合是否可能
    benford    Benford 首位数定律分析 (适用于跨数量级的大批数字)
    digits     末位数字均匀性检验 (检测编造/过度修约)
    tortured   "tortured phrases" 折磨型短语检测 (洗稿/翻译规避查重的痕迹)
    aitext     未披露的 LLM 生成文本指纹检测
    scan-table 对 CSV 表格批量跑 GRIM/GRIMMER
    selftest   运行内置自检 (验证算法实现正确)

示例 / examples:
    python3 forensics.py grim --mean 5.19 --n 28
    python3 forensics.py grimmer --mean 3.45 --sd 1.12 --n 20
    python3 forensics.py benford --file numbers.txt
    python3 forensics.py digits --numbers "12.3, 45.6, 78.0, 90.5"
    python3 forensics.py tortured --file paper.txt
    python3 forensics.py aitext --file paper.txt
    python3 forensics.py scan-table --file table.csv
    python3 forensics.py selftest
"""

import argparse
import json
import math
import os
import re
import sys

EPS = 1e-9
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


# --------------------------------------------------------------------------- #
#  数学基础：卡方分布生存函数 (chi-square survival function, no scipy)
# --------------------------------------------------------------------------- #
def _gammaln(x):
    return math.lgamma(x)


def _lower_gamma_reg(s, x):
    """Regularized lower incomplete gamma P(s, x) via series / continued fraction.
    Ported from Numerical Recipes (gammp/gammq). Accurate for s>0, x>=0."""
    if x < 0 or s <= 0:
        raise ValueError("invalid args to lower incomplete gamma")
    if x == 0:
        return 0.0
    if x < s + 1.0:
        # series representation
        ap = s
        total = 1.0 / s
        delta = total
        for _ in range(1000):
            ap += 1.0
            delta *= x / ap
            total += delta
            if abs(delta) < abs(total) * 1e-15:
                break
        return total * math.exp(-x + s * math.log(x) - _gammaln(s))
    else:
        # continued fraction for the complementary function Q, then P = 1 - Q
        tiny = 1e-300
        b = x + 1.0 - s
        c = 1.0 / tiny
        d = 1.0 / b
        h = d
        for i in range(1, 1000):
            an = -i * (i - s)
            b += 2.0
            d = an * d + b
            if abs(d) < tiny:
                d = tiny
            c = b + an / c
            if abs(c) < tiny:
                c = tiny
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < 1e-15:
                break
        q = math.exp(-x + s * math.log(x) - _gammaln(s)) * h
        return 1.0 - q


def chi2_sf(stat, df):
    """Upper-tail probability P(X > stat) for chi-square with df degrees of freedom."""
    if stat <= 0:
        return 1.0
    return max(0.0, 1.0 - _lower_gamma_reg(df / 2.0, stat / 2.0))


# --------------------------------------------------------------------------- #
#  数字解析工具
# --------------------------------------------------------------------------- #
_NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def count_decimals(text):
    """Number of digits after the decimal point in a numeric *string*."""
    text = text.strip()
    m = re.search(r"\.(\d+)", text)
    return len(m.group(1)) if m else 0


def parse_numbers(blob):
    """Extract all numeric tokens from arbitrary text."""
    return [float(m) for m in _NUM_RE.findall(blob)]


def _load_input(args, label="数字"):
    """Return raw text from --file or --numbers."""
    if getattr(args, "file", None):
        with open(args.file, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    if getattr(args, "numbers", None):
        return args.numbers
    sys.exit(f"错误：请用 --file 或 --numbers 提供{label}。")


# --------------------------------------------------------------------------- #
#  GRIM test
# --------------------------------------------------------------------------- #
def grim_consistent(mean_str, n, items=1):
    """
    GRIM (Granularity-Related Inconsistency of Means), Brown & Heathers (2017).

    对整数型数据 (李克特量表、计数、整数评分)，报告的均值 M = sum/(n*items)，
    其中 sum 必为整数。给定 M 的小数位数，检验是否存在整数 sum 使得
    round(sum/(n*items)) == M。返回 (consistent, info)。
    使用区间法，对四舍五入规则稳健。
    """
    decimals = count_decimals(mean_str)
    mean = float(mean_str)
    n_eff = n * items
    if n_eff <= 0:
        raise ValueError("n 与 items 必须为正")
    u = 10.0 ** (-decimals)                       # rounding unit
    lo = (mean - 0.5 * u) * n_eff                 # smallest compatible integer sum
    hi = (mean + 0.5 * u) * n_eff                 # exclusive upper bound
    first_int = math.ceil(lo - EPS)
    consistent = first_int < hi + EPS
    # power note: GRIM only bites when granularity is coarser than rounding
    has_power = n_eff < 10 ** decimals if decimals > 0 else False
    closest_sum = round(mean * n_eff)
    info = {
        "decimals": decimals,
        "n_eff": n_eff,
        "closest_integer_sum": closest_sum,
        "reconstructed_mean": round(closest_sum / n_eff, decimals + 2),
        "has_power": has_power,
    }
    return consistent, info


def cmd_grim(args):
    consistent, info = grim_consistent(args.mean, args.n, args.items)
    print("═" * 56)
    print(f"  GRIM 检验：mean={args.mean}  n={args.n}  items={args.items}")
    print("═" * 56)
    print(f"  小数位数        : {info['decimals']}")
    print(f"  有效样本量 n_eff: {info['n_eff']}")
    print(f"  最接近的整数和  : {info['closest_integer_sum']}")
    print(f"  反推均值        : {info['reconstructed_mean']}")
    if not info["has_power"] and info["decimals"] > 0:
        print("  ⚠ 注意：n_eff ≥ 10^小数位，GRIM 此时几乎总是通过，无判别力。")
    if consistent:
        print("  结论            : ✅ 一致 (该均值在数学上可能成立)")
    else:
        print("  结论            : 🔴 不一致 (该均值在整数数据下不可能出现！)")
        print("  → 这是一个硬性数学矛盾，强烈建议核对原始数据或方法描述。")
    print("═" * 56)
    return 0 if consistent else 2


# --------------------------------------------------------------------------- #
#  GRIMMER test
# --------------------------------------------------------------------------- #
def grimmer_consistent(mean_str, sd_str, n, items=1):
    """
    GRIMMER (Anaya 2016; Allard 2018) — 在 GRIM 基础上加入对标准差的检验。
    对整数型数据，检验 (mean, sd, n) 组合是否数学自洽。

    步骤：
      1. 先做 GRIM。均值本身不可能 → 直接不一致。
      2. 由报告的 SD 的修约区间求出平方和 Σx² 的可行区间。
      3. Σx² 必须为整数，且满足奇偶约束 Σx² ≡ Σx (mod 2)
         (因 x² ≡ x (mod 2)，故对整数样本恒成立)。
      4. 若区间内不存在满足奇偶性的整数 Σx² → 不一致。
    这是"必要条件"检验：能证伪，不能证真。
    """
    grim_ok, ginfo = grim_consistent(mean_str, n, items)
    n_eff = n * items
    mean = float(mean_str)
    sd = float(sd_str)
    dec_sd = count_decimals(sd_str)
    sum_x = ginfo["closest_integer_sum"]

    reasons = []
    if not grim_ok:
        reasons.append("均值未通过 GRIM (整数和不存在)")

    u = 10.0 ** (-dec_sd)
    sd_lo = max(0.0, sd - 0.5 * u)
    sd_hi = sd + 0.5 * u
    # sample variance uses ddof=1
    if n <= 1:
        raise ValueError("n 必须 > 1")
    ss_lo = sd_lo ** 2 * (n - 1)
    ss_hi = sd_hi ** 2 * (n - 1)
    sumsq_lo = ss_lo + sum_x ** 2 / n_eff
    sumsq_hi = ss_hi + sum_x ** 2 / n_eff
    lo_int = math.ceil(sumsq_lo - EPS)
    hi_int = math.floor(sumsq_hi + EPS)

    parity_ok = False
    if hi_int >= lo_int:
        for cand in range(lo_int, hi_int + 1):
            if cand % 2 == sum_x % 2:
                parity_ok = True
                break
        if not parity_ok:
            reasons.append("Σx² 整数区间内无满足奇偶约束的解")
    else:
        reasons.append("由 SD 反推的 Σx² 区间内不存在整数解")

    consistent = grim_ok and parity_ok and hi_int >= lo_int
    info = dict(ginfo)
    info.update({
        "sd_decimals": dec_sd,
        "sumsq_int_range": [lo_int, hi_int] if hi_int >= lo_int else None,
        "reasons": reasons,
    })
    return consistent, info


def cmd_grimmer(args):
    consistent, info = grimmer_consistent(args.mean, args.sd, args.n, args.items)
    print("═" * 56)
    print(f"  GRIMMER 检验：mean={args.mean}  sd={args.sd}  n={args.n}")
    print("═" * 56)
    print(f"  整数和 (由均值)  : {info['closest_integer_sum']}")
    rng = info["sumsq_int_range"]
    print(f"  Σx² 可行整数区间 : {rng if rng else '空 (无解)'}")
    if consistent:
        print("  结论             : ✅ 一致 (mean+sd 组合数学上可能)")
    else:
        print("  结论             : 🔴 不一致")
        for r in info["reasons"]:
            print(f"      • {r}")
        print("  → 整数型数据出现该 (均值, 标准差) 组合在数学上不可能。")
    print("═" * 56)
    return 0 if consistent else 2


# --------------------------------------------------------------------------- #
#  Benford 首位数定律
# --------------------------------------------------------------------------- #
def benford_expected():
    return {d: math.log10(1 + 1.0 / d) for d in range(1, 10)}


def first_significant_digit(x):
    x = abs(x)
    if x == 0:
        return None
    while x < 1:
        x *= 10
    while x >= 10:
        x /= 10
    return int(x)


def benford_analysis(numbers):
    digits = [first_significant_digit(x) for x in numbers]
    digits = [d for d in digits if d]
    n = len(digits)
    if n == 0:
        return None
    obs = {d: 0 for d in range(1, 10)}
    for d in digits:
        obs[d] += 1
    exp = benford_expected()
    chi2 = sum((obs[d] - exp[d] * n) ** 2 / (exp[d] * n) for d in range(1, 10))
    mad = sum(abs(obs[d] / n - exp[d]) for d in range(1, 10)) / 9
    # Nigrini (2012) first-digit MAD conformity thresholds
    if mad < 0.006:
        conformity = "紧密符合 (close conformity)"
    elif mad < 0.012:
        conformity = "可接受 (acceptable conformity)"
    elif mad < 0.015:
        conformity = "勉强符合 (marginal conformity)"
    else:
        conformity = "不符合 (non-conformity) ⚠"
    return {
        "n": n, "observed": obs, "expected": exp,
        "chi2": chi2, "df": 8, "p": chi2_sf(chi2, 8),
        "mad": mad, "conformity": conformity,
    }


def cmd_benford(args):
    nums = parse_numbers(_load_input(args))
    res = benford_analysis(nums)
    if not res:
        sys.exit("没有可用于 Benford 分析的正数。")
    print("═" * 56)
    print(f"  Benford 首位数定律分析   (有效数字个数 n={res['n']})")
    print("═" * 56)
    if res["n"] < 50:
        print("  ⚠ 样本偏小 (n<50)，Benford 检验不可靠，仅供参考。")
    print("  位  观测%   期望%   偏差")
    for d in range(1, 10):
        o = res["observed"][d] / res["n"] * 100
        e = res["expected"][d] * 100
        bar = "█" * int(round(o / 2))
        print(f"   {d}  {o:5.1f}  {e:5.1f}   {o-e:+5.1f}  {bar}")
    print("─" * 56)
    print(f"  卡方 = {res['chi2']:.2f} (df=8)   p = {res['p']:.4f}")
    print(f"  MAD  = {res['mad']:.4f}  →  {res['conformity']}")
    print("  注意：Benford 仅适用于跨多个数量级、无人为上下限的自然数据；")
    print("        对受限量表 / 百分比 / 单一量级数据不适用。")
    print("═" * 56)
    return 2 if (res["mad"] >= 0.015 and res["n"] >= 50) else 0


# --------------------------------------------------------------------------- #
#  末位数字均匀性
# --------------------------------------------------------------------------- #
def terminal_digit_analysis(number_strings):
    """Last-digit distribution should be ~uniform for measured data."""
    last = []
    for s in number_strings:
        s = s.strip()
        m = re.search(r"(\d)(?!.*\d)", s)  # last digit char in the token
        if m:
            last.append(int(m.group(1)))
    n = len(last)
    if n == 0:
        return None
    obs = {d: 0 for d in range(10)}
    for d in last:
        obs[d] += 1
    expected = n / 10.0
    chi2 = sum((obs[d] - expected) ** 2 / expected for d in range(10))
    return {
        "n": n, "observed": obs, "expected": expected,
        "chi2": chi2, "df": 9, "p": chi2_sf(chi2, 9),
        "round_share": (obs[0] + obs[5]) / n,
    }


def cmd_digits(args):
    blob = _load_input(args)
    tokens = _NUM_RE.findall(blob)
    res = terminal_digit_analysis(tokens)
    if not res:
        sys.exit("没有可分析的数字末位。")
    print("═" * 56)
    print(f"  末位数字均匀性检验   (n={res['n']}, 期望每位 {res['expected']:.1f})")
    print("═" * 56)
    for d in range(10):
        o = res["observed"][d]
        bar = "█" * int(round(o / max(1, res["n"]) * 50))
        print(f"   末位 {d}: {o:4d}  {bar}")
    print("─" * 56)
    print(f"  卡方 = {res['chi2']:.2f} (df=9)   p = {res['p']:.4f}")
    print(f"  0/5 占比 = {res['round_share']*100:.1f}% (期望 ~20%)")
    if res["p"] < 0.05:
        print("  🔴 末位分布显著偏离均匀 (p<0.05)，可能存在编造或过度修约。")
    else:
        print("  ✅ 末位分布未见显著异常。")
    print("═" * 56)
    return 2 if res["p"] < 0.05 else 0


# --------------------------------------------------------------------------- #
#  文本：tortured phrases
# --------------------------------------------------------------------------- #
def _load_json(name):
    with open(os.path.join(DATA_DIR, name), "r", encoding="utf-8") as fh:
        return json.load(fh)


def find_tortured(text):
    data = _load_json("tortured_phrases.json")
    low = text.lower()
    hits = []
    for entry in data["entries"]:
        for variant in entry["tortured"]:
            idx = low.find(variant.lower())
            if idx != -1:
                ctx = text[max(0, idx - 40): idx + len(variant) + 40].replace("\n", " ")
                hits.append({
                    "tortured": variant, "canonical": entry["canonical"],
                    "confidence": entry["confidence"], "context": ctx.strip(),
                })
    return hits


def cmd_tortured(args):
    text = _load_input(args, "文本")
    hits = find_tortured(text)
    print("═" * 56)
    print("  Tortured phrases (折磨型短语) 检测")
    print("═" * 56)
    if not hits:
        print("  ✅ 未发现已知的折磨型短语。")
    else:
        order = {"high": 0, "medium": 1, "low": 2}
        for h in sorted(hits, key=lambda x: order.get(x["confidence"], 9)):
            flag = {"high": "🔴", "medium": "🟠", "low": "🟡"}[h["confidence"]]
            print(f"  {flag} “{h['tortured']}”  (应为 “{h['canonical']}”)")
            print(f"      …{h['context']}…")
        print("─" * 56)
        print(f"  共 {len(hits)} 处。高置信度命中通常是洗稿/同义词替换工具的铁证。")
    print("═" * 56)
    return 2 if any(h["confidence"] == "high" for h in hits) else 0


# --------------------------------------------------------------------------- #
#  文本：AI 生成文本指纹
# --------------------------------------------------------------------------- #
def find_ai_fingerprints(text):
    data = _load_json("ai_fingerprints.json")
    low = text.lower()
    guns = []
    for item in data["smoking_guns"]:
        idx = low.find(item["phrase"])
        if idx != -1:
            ctx = text[max(0, idx - 30): idx + len(item["phrase"]) + 50].replace("\n", " ")
            guns.append({"phrase": item["phrase"], "confidence": item["confidence"],
                         "context": ctx.strip()})
    words = re.findall(r"[a-zA-Z']+", low)
    wc = max(1, len(words))
    fillers = {}
    wordset = words
    for w in data["filler_words"]:
        c = wordset.count(w)
        if c:
            fillers[w] = c
    bigrams = {}
    for bg in data["filler_bigrams"]:
        c = low.count(bg)
        if c:
            bigrams[bg] = c
    filler_total = sum(fillers.values()) + sum(bigrams.values())
    density = filler_total / wc * 1000
    return {"smoking_guns": guns, "fillers": fillers, "bigrams": bigrams,
            "word_count": wc, "filler_per_1k": density}


def cmd_aitext(args):
    text = _load_input(args, "文本")
    res = find_ai_fingerprints(text)
    print("═" * 56)
    print("  未披露 AI 生成文本指纹检测")
    print("═" * 56)
    if res["smoking_guns"]:
        print("  🔴 发现高度可疑的聊天机器人残留语句：")
        for g in res["smoking_guns"]:
            print(f"      • “{g['phrase']}”")
            print(f"        …{g['context']}…")
    else:
        print("  ✅ 未发现明显的 LLM 残留语句 (如 “as an AI language model”)。")
    print("─" * 56)
    print(f"  文本词数 ~{res['word_count']}，AI 偏好填充词密度 = "
          f"{res['filler_per_1k']:.1f} / 千词")
    if res["fillers"]:
        top = sorted(res["fillers"].items(), key=lambda kv: -kv[1])[:8]
        print("  高频填充词: " + ", ".join(f"{w}×{c}" for w, c in top))
    if res["filler_per_1k"] > 15:
        print("  🟠 填充词密度偏高，可能为 AI 润色/生成 (弱信号，需结合其他证据)。")
    print("  ⚠ 填充词只是风格弱信号，绝不能单独作为定论依据。")
    print("═" * 56)
    return 2 if res["smoking_guns"] else 0


# --------------------------------------------------------------------------- #
#  扫描 CSV 表格：自动跑 GRIM / GRIMMER
# --------------------------------------------------------------------------- #
def cmd_scan_table(args):
    import csv
    with open(args.file, newline="", encoding="utf-8", errors="replace") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit("CSV 为空或无表头。")
    cols = {c.lower(): c for c in rows[0].keys()}

    def pick(*names):
        for nm in names:
            if nm in cols:
                return cols[nm]
        return None

    mc = pick("mean", "m", "均值")
    sc = pick("sd", "std", "标准差")
    nc = pick("n", "样本量")
    ic = pick("items", "k")
    if not (mc and nc):
        sys.exit("CSV 需要至少包含 mean 与 n 两列 (可选 sd, items)。")
    print("═" * 64)
    print(f"  批量 GRIM/GRIMMER 扫描：{os.path.basename(args.file)} ({len(rows)} 行)")
    print("═" * 64)
    flagged = 0
    for i, row in enumerate(rows, 1):
        try:
            n = int(float(row[nc]))
            items = int(float(row[ic])) if ic and row.get(ic) else 1
            mean_str = str(row[mc]).strip()
            if sc and row.get(sc):
                ok, _ = grimmer_consistent(mean_str, str(row[sc]).strip(), n, items)
                test = "GRIMMER"
            else:
                ok, _ = grim_consistent(mean_str, n, items)
                test = "GRIM"
        except (ValueError, ZeroDivisionError, KeyError) as exc:
            print(f"  行{i}: 跳过 ({exc})")
            continue
        if not ok:
            flagged += 1
            extra = f" sd={row[sc]}" if sc and row.get(sc) else ""
            print(f"  🔴 行{i}: {test} 不一致  mean={mean_str}{extra} n={n}")
    print("─" * 64)
    print(f"  共标记 {flagged} 行存在数学矛盾。" if flagged else "  ✅ 未发现数学矛盾。")
    print("═" * 64)
    return 2 if flagged else 0


# --------------------------------------------------------------------------- #
#  自检
# --------------------------------------------------------------------------- #
def cmd_selftest(args):
    import random
    passed, failed = 0, 0

    def check(name, cond):
        nonlocal passed, failed
        if cond:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name}")

    print("── chi2_sf 校验 ──")
    # known: chi2=15.507, df=8 → p≈0.05 ; chi2=16.919, df=9 → p≈0.05
    check("chi2_sf(15.507, 8) ≈ 0.05", abs(chi2_sf(15.507, 8) - 0.05) < 0.005)
    check("chi2_sf(16.919, 9) ≈ 0.05", abs(chi2_sf(16.919, 9) - 0.05) < 0.005)
    check("chi2_sf(0, 5) == 1", abs(chi2_sf(0, 5) - 1.0) < 1e-9)
    check("chi2_sf(3.841, 1) ≈ 0.05", abs(chi2_sf(3.841, 1) - 0.05) < 0.005)

    print("── GRIM 校验 ──")
    # classic inconsistent case (Brown & Heathers): mean 5.19, n 28
    ok, _ = grim_consistent("5.19", 28)
    check("mean=5.19,n=28 → 不一致", not ok)
    ok, _ = grim_consistent("5.18", 28)
    check("mean=5.18,n=28 → 一致", ok)
    ok, _ = grim_consistent("1.5", 2)
    check("mean=1.5,n=2 → 一致", ok)
    ok, _ = grim_consistent("3.14", 7)  # 3.14*7=21.98 → 22/7=3.142857→3.14 consistent
    check("mean=3.14,n=7 → 一致", ok)
    ok, _ = grim_consistent("2.50", 3)  # 2.5*3=7.5; 7/3=2.33,8/3=2.67 → neither rounds to 2.50
    check("mean=2.50,n=3 → 不一致", not ok)

    print("── GRIMMER 校验 (随机整数样本应自洽) ──")
    rng = random.Random(20240621)
    all_pass = True
    for _ in range(200):
        n = rng.randint(4, 12)
        sample = [rng.randint(1, 7) for _ in range(n)]
        m = sum(sample) / n
        var = sum((x - m) ** 2 for x in sample) / (n - 1)
        sd = math.sqrt(var)
        mean_str = f"{m:.2f}"
        sd_str = f"{sd:.2f}"
        ok, _ = grimmer_consistent(mean_str, sd_str, n)
        if not ok:
            all_pass = False
            print(f"     反例: sample={sample} mean={mean_str} sd={sd_str}")
            break
    check("200 个随机整数样本全部判为一致", all_pass)
    # an impossible combo: integer data, n=3, mean=4.00 (sum=12) but sd=0.10 too small?
    # sum=12 with n=3 integers; min nonzero sample variance for distinct-ish; test a clearly impossible one
    ok, _ = grimmer_consistent("4.00", "0.30", 3)  # sd=0.3 → SS=0.18; needs Σx²=48.18.. no integer w/ parity
    check("mean=4.00,sd=0.30,n=3 → 不一致", not ok)

    print("── Benford 校验 ──")
    # Benford-distributed-ish: powers give first-digit 1 dominance
    benford_set = [1.0 * (10 ** (i / 23.0)) for i in range(300)]
    res = benford_analysis(benford_set)
    check("几何级数数据 Benford MAD 低", res["mad"] < 0.05)

    print("── 文本检测 校验 ──")
    th = find_tortured("We used a counterfeit consciousness model on the informational index.")
    check("命中 counterfeit consciousness", any(h["tortured"] == "counterfeit consciousness" for h in th))
    check("命中 informational index", any(h["tortured"] == "informational index" for h in th))
    ai = find_ai_fingerprints("Certainly, here is a possible introduction. As an AI language model, I cannot browse.")
    check("命中 as an ai language model", any("as an ai language model" in g["phrase"] for g in ai["smoking_guns"]))

    print("─" * 56)
    print(f"  通过 {passed} 项，失败 {failed} 项。")
    return 0 if failed == 0 else 1


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #
def build_parser():
    p = argparse.ArgumentParser(
        prog="forensics.py",
        description="耿同学打假工具箱 — 统计与文本取证 CLI (纯标准库)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("grim", help="GRIM 均值一致性检验")
    g.add_argument("--mean", required=True, help="报告的均值 (保留原始小数位, 如 5.19)")
    g.add_argument("--n", type=int, required=True, help="样本量")
    g.add_argument("--items", type=int, default=1, help="量表条目数 (默认 1)")
    g.set_defaults(func=cmd_grim)

    gm = sub.add_parser("grimmer", help="GRIMMER 均值+标准差一致性检验")
    gm.add_argument("--mean", required=True)
    gm.add_argument("--sd", required=True, help="报告的标准差 (保留原始小数位)")
    gm.add_argument("--n", type=int, required=True)
    gm.add_argument("--items", type=int, default=1)
    gm.set_defaults(func=cmd_grimmer)

    b = sub.add_parser("benford", help="Benford 首位数定律分析")
    b.add_argument("--file")
    b.add_argument("--numbers")
    b.set_defaults(func=cmd_benford)

    d = sub.add_parser("digits", help="末位数字均匀性检验")
    d.add_argument("--file")
    d.add_argument("--numbers")
    d.set_defaults(func=cmd_digits)

    t = sub.add_parser("tortured", help="折磨型短语检测")
    t.add_argument("--file")
    t.add_argument("--numbers", dest="numbers", help=argparse.SUPPRESS)
    t.set_defaults(func=cmd_tortured)

    a = sub.add_parser("aitext", help="AI 生成文本指纹检测")
    a.add_argument("--file")
    a.add_argument("--numbers", dest="numbers", help=argparse.SUPPRESS)
    a.set_defaults(func=cmd_aitext)

    s = sub.add_parser("scan-table", help="对 CSV 批量跑 GRIM/GRIMMER")
    s.add_argument("--file", required=True)
    s.set_defaults(func=cmd_scan_table)

    st = sub.add_parser("selftest", help="运行内置自检")
    st.set_defaults(func=cmd_selftest)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

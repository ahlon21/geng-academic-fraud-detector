#!/usr/bin/env python3
"""
scripts/fraud_tools.py — 耿同学学术打假工具层

为纯 prompt 的 SKILL.md 补充像素级/统计级检测能力。
核心原则：LLM 负责推理和判断，本模块负责提供 LLM 无法精确完成的数值计算。

依赖：pip install pillow scipy numpy opencv-python-headless scikit-image
"""

import io
import math
import itertools
from pathlib import Path
from typing import List, Tuple, Optional

import numpy as np
from scipy import stats as sp_stats

# ─── 模块一：数值数据造假检测 ─────────────────────────────────────

def benford_first_digit(data: List[float]) -> dict:
    """
    Benford 定律第一位数字检测。

    真实数据的第一位数字分布遵循 P(d) = log10(1 + 1/d)。
    论文表格中的数据（尤其是计数/测量值）若严重偏离 Benford，
    高度可疑是编造或篡改。

    适用于：细胞计数、荧光强度、Western blot 定量、qPCR 的 Ct 值等。
    """
    first_digits = []
    for v in data:
        v = abs(v)
        if v == 0:
            continue
        # 取第一位数字（1-9）
        s = f"{v:.10e}"  # 科学计数法避免浮点问题
        fd = int(s[0])
        if 1 <= fd <= 9:
            first_digits.append(fd)

    if len(first_digits) < 30:
        return {"error": "样本量不足（需要 >=30 个有效值）", "n": len(first_digits)}

    observed = np.bincount(first_digits, minlength=10)[1:]  # 索引1-9
    expected = np.array([math.log10(1 + 1/d) for d in range(1, 10)]) * len(first_digits)

    chi2, pval = sp_stats.chisquare(f_obs=observed, f_exp=expected)
    # 计算 MAD（平均绝对偏差），业界常用
    proportions_obs = observed / len(first_digits)
    proportions_exp = expected / len(first_digits)
    mad = np.mean(np.abs(proportions_obs - proportions_exp))

    # Nigrini 的 MAD 判定标准
    if mad < 0.006:
        conformity = "高度符合"
    elif mad < 0.015:
        conformity = "大致符合"
    elif mad < 0.03:
        conformity = "边缘异常"
    else:
        conformity = "显著偏离 ⚠️"

    return {
        "n": len(first_digits),
        "chi2": float(chi2),
        "p_value": float(pval),
        "mad": float(mad),
        "conformity": conformity,
        "observed_distribution": observed.tolist(),
        "expected_distribution": [round(e, 1) for e in expected],
        "interpretation": (
            f"Benford 第一位数字检测：{conformity}"
            f"（MAD={mad:.4f}, χ²={chi2:.2f}, p={pval:.4f}）"
        ),
    }


def benford_second_digit(data: List[float]) -> dict:
    """
    Benford 定律第二位数字检测（灵敏度高于第一位）。
    编造数据的第二位数字分布往往比第一位更异常。
    """
    second_digits = []
    for v in data:
        v = abs(v)
        if v == 0:
            continue
        s = f"{v:.10e}"
        if len(s) >= 2:
            sd = int(s[1])
            second_digits.append(sd)

    if len(second_digits) < 30:
        return {"error": "样本量不足", "n": len(second_digits)}

    observed = np.bincount(second_digits, minlength=10)
    # Benford 第二位的理论分布
    p_second = [sum(math.log10(1 + 1/(10*k + d)) for k in range(1, 10)) for d in range(10)]
    expected = np.array(p_second) * len(second_digits)

    chi2, pval = sp_stats.chisquare(f_obs=observed, f_exp=expected)

    proportions_obs = observed / len(second_digits)
    proportions_exp = expected / len(second_digits)
    mad = np.mean(np.abs(proportions_obs - proportions_exp))

    if mad < 0.01:
        conformity = "正常"
    elif mad < 0.02:
        conformity = "轻微异常"
    elif mad < 0.04:
        conformity = "明显异常 ⚠️"
    else:
        conformity = "严重异常 🚨"

    return {
        "n": len(second_digits),
        "chi2": float(chi2),
        "p_value": float(pval),
        "mad": float(mad),
        "conformity": conformity,
        "interpretation": (
            f"Benford 第二位数字检测：{conformity}"
            f"（MAD={mad:.4f}, p={pval:.4f}）"
        ),
    }


def last_digit_uniformity(data: List[float], sig_digits: int = 1) -> dict:
    """
    末位数字均匀性检验（耿同学第二式的核心检测）。

    真实数据的末位数字应该近似均匀分布（每个数字 ~10%）。
    如果末位数字分布严重偏斜 → 数据高度可疑是人为编造。

    sig_digits: 检验小数的最后几位（1=小数点后1位，0=整数末位）
    """
    last_digits = []
    for v in data:
        v = abs(v)
        s = f"{v:.10f}"  # 足够精度
        # 取第 sig_digits 位小数
        decimal_part = s.split('.')[1] if '.' in s else "0"
        if len(decimal_part) >= sig_digits:
            ld = int(decimal_part[sig_digits - 1])
            last_digits.append(ld)

    if len(last_digits) < 30:
        return {"error": "样本量不足", "n": len(last_digits)}

    observed = np.bincount(last_digits, minlength=10)
    expected = np.full(10, len(last_digits) / 10)

    chi2, pval = sp_stats.chisquare(f_obs=observed, f_exp=expected)
    uniformity = max(observed) / min(observed) if min(observed) > 0 else float('inf')

    # 判定：均匀分布下 max/min 应接近1
    if uniformity < 2:
        verdict = "末位分布正常"
    elif uniformity < 3:
        verdict = "末位分布偏斜 ⚠️（建议关注）"
    else:
        verdict = f"末位分布严重偏斜 🚨（max/min={uniformity:.1f}）"

    return {
        "n": len(last_digits),
        "chi2": float(chi2),
        "p_value": float(pval),
        "uniformity_ratio": float(uniformity),
        "observed": observed.tolist(),
        "verdict": verdict,
    }


def grimm_test(mean: float, sd: float, n: int) -> dict:
    """
    GRIM（Granularity-Related Inconsistency of Means）检验。
    当均值以某种精度报告时，检查报告的均值和 SD 是否与整数计数的粒度一致。

    例如：n=3，均值报告为 45.3 —— 三个整数的均值末位只能是 .0/.333/.667。
    如果报告的均值末位与整数计数粒度不匹配 → 数据造假 🚨

    参考：Brown & Heathers (2017). The GRIM test.
    """
    if n <= 0 or sd < 0:
        return {"error": "无效参数"}

    # 确定均值的粒度（小数点后几位）
    mean_str = f"{mean}"
    if '.' in mean_str:
        precision = len(mean_str.split('.')[1])
    else:
        precision = 0

    granularity = 10 ** (-precision)
    # n 个整数的均值可能值为 k/n * granularity 的整数倍
    # 检查均值是否可以由 n 个整数得到
    possible_sums = np.arange(round(mean * n / granularity) - 2,
                               round(mean * n / granularity) + 3)
    consistent = any(
        abs(mean - s * granularity / n) < 1e-10
        for s in possible_sums
    )

    # SD 一致性检验：从均值±SD反推原始数据是否可能
    # 简版：检查 SD 是否与整数粒度匹配
    sd_consistent = True
    if n > 1:
        # 对于 n 个整数，理论上 SD 的平方必须为整数差平方和除 n
        # 这里做粗略检查
        ss = sd ** 2 * n
        if abs(ss - round(ss)) > 1e-6:
            sd_consistent = False

    result = {
        "mean_grim_consistent": consistent,
        "sd_grim_consistent": sd_consistent,
    }

    if not consistent and not sd_consistent:
        result["verdict"] = "🎯 GRIM+SD 均不一致 → 数据高度可疑"
    elif not consistent:
        result["verdict"] = "⚠️ GRIM 不一致（均值与整数粒度冲突）"
    elif not sd_consistent:
        result["verdict"] = "⚠️ SD 与整数粒度冲突（建议核实原始数据）"
    else:
        result["verdict"] = "✅ GRIM+SD 一致"

    return result


def sd_consistency_check(groups: List[Tuple[float, float, int]]) -> dict:
    """
    检查多组数据中 SD 的一致性（耿同学经典手法）。

    如果多组"独立实验"报告的 SD 完全相同或呈现规律性 →
    数据高度可疑。

    groups: [(mean1, sd1, n1), (mean2, sd2, n2), ...]
    """
    sds = [g[1] for g in groups]
    ns = [g[2] for g in groups]

    # 检查 SD 是否完全相同
    sd_unique = len(set(round(s, 6) for s in sds))
    if sd_unique == 1 and len(groups) > 1:
        return {
            "alarm": "🚨 所有组的 SD 完全相同！数据极有可能编造",
            "sd_unique_count": 1,
            "sd_values": [round(s, 4) for s in sds],
        }

    # Levene 检验：多组方差是否齐性（真实数据通常不等方差的组差异大）
    if len(groups) >= 2 and all(n >= 2 for n in ns):
        # 模拟数据分布做 Levene 检验
        simulated_data = []
        group_labels = []
        for i, (m, sd, n) in enumerate(groups):
            np.random.seed(42)  # 固定种子以确保可复现
            simulated = np.random.normal(m, sd, n)
            simulated_data.extend(simulated)
            group_labels.extend([i] * n)

        stat, pval = sp_stats.levene(*[
            np.random.normal(m, sd, n)
            for m, sd, n in groups
        ])

        # 计算 SD 的变异系数
        sd_mean = np.mean(sds)
        sd_cv = np.std(sds) / sd_mean if sd_mean > 0 else 0

        assessment = (
            "正常" if sd_cv < 0.15
            else "略有波动" if sd_cv < 0.3
            else "波动较大（正常）" if sd_cv < 0.5
            else "SD 差异异常 ⚠️"
        )

        return {
            "levene_stat": float(stat),
            "levene_p": float(pval),
            "sd_cv": float(sd_cv),
            "sd_values": [round(s, 4) for s in sds],
            "assessment": assessment,
            "sd_cv_interpretation": (
                f"SD 变异系数 = {sd_cv:.3f}（{assessment}）"
            ),
        }

    return {
        "sd_values": [round(s, 4) for s in sds],
        "note": "样本量不足做 Levene 检验",
    }


def column_difference_test(columns: List[List[float]]) -> dict:
    """
    列间差值恒定检验（耿同学经典手法——同济王平案）。

    检查两列数据的差值是否恒定。如果不同实验条件下的数据
    列之间的差值完全相同 → 数据不是实验测量而是加减法得到。

    columns: [[col1_val1, col1_val2, ...], [col2_val1, ...], ...]
    """
    if len(columns) < 2:
        return {"error": "至少需要2列数据"}

    results = []
    for i, j in itertools.combinations(range(len(columns)), 2):
        c1, c2 = np.array(columns[i]), np.array(columns[j])
        if len(c1) != len(c2):
            continue
        diffs = c1 - c2
        diff_std = np.std(diffs) if len(diffs) > 1 else 0
        diff_mean = np.mean(diffs)

        # 如果差值几乎恒定（标准差极小）
        if abs(diff_mean) > 1e-10:  # 排除全零差
            relative_var = diff_std / abs(diff_mean)
        else:
            relative_var = diff_std

        is_constant = relative_var < 0.001 and diff_std < 1e-6

        results.append({
            "col_pair": f"列{i+1} vs 列{j+1}",
            "mean_diff": float(diff_mean),
            "std_diff": float(diff_std),
            "relative_variation": float(relative_var),
            "is_constant_diff": bool(is_constant),
            "alarm": "🚨 差值恒定!" if is_constant else "正常",
        })

    return {"column_comparisons": results}


def p_value_anomaly(p_values: List[float]) -> dict:
    """
    p-hacking 检测（第四式统计异常）。

    检查一组 p 值是否异常集中在 0.04-0.05 区间（人为操纵）。
    同时检测 p 值的末位分布是否均匀。

    正常：p 值应在 0-1 均匀分布（或按研究领域有合理分布）
    异常：大量 p 值恰好 < 0.05 但 > 0.04
    """
    if not p_values:
        return {"error": "无 p 值数据"}

    total = len(p_values)

    # 区间分布
    bins = {
        "<0.01": sum(1 for p in p_values if p < 0.01),
        "0.01-0.04": sum(1 for p in p_values if 0.01 <= p < 0.04),
        "0.04-0.05": sum(1 for p in p_values if 0.04 <= p <= 0.05),
        "0.05-0.10": sum(1 for p in p_values if 0.05 < p <= 0.10),
        ">0.10": sum(1 for p in p_values if p > 0.10),
    }

    # p-hacking 判定：大量 p 值挤在 0.04-0.05
    p_hacking_zone_ratio = bins["0.04-0.05"] / total

    if p_hacking_zone_ratio > 0.3 and total >= 5:
        phacking = "🚨 高度疑似 p-hacking " \
                   f"（{bins['0.04-0.05']}/{total} 集中在 0.04-0.05）"
    elif p_hacking_zone_ratio > 0.15:
        phacking = "⚠️ 需要关注 p-hacking 风险"
    else:
        phacking = "✅ 未发现明显 p-hacking"

    # Fisher 综合检验
    if total >= 3:
        # Fisher's method: 组合 p 值
        fisher_stat = -2 * sum(math.log(p) for p in p_values if p > 0)
        combined_p = 1 - sp_stats.chi2.cdf(fisher_stat, 2 * total)
    else:
        combined_p = None

    return {
        "n_p_values": total,
        "distribution": bins,
        "p_hacking_zone_ratio": float(p_hacking_zone_ratio),
        "phacking_verdict": phacking,
        "fisher_combined_p": float(combined_p) if combined_p else None,
    }


# ─── 模块二：图像检测 ─────────────────────────────────────

def try_import_image_tools():
    """检查图像工具是否可用"""
    try:
        import cv2
        from PIL import Image
        from skimage.metrics import structural_similarity as ssim
        return True
    except ImportError:
        return False


def image_ssim(path_a: str, path_b: str) -> dict:
    """
    结构相似性指数（SSIM）比对。
    两张图片如果 SSIM > 0.95 → 极有可能是同一张图旋转/裁剪后的复用。
    这是耿同学第一式的核心像素级检测。
    """
    if not try_import_image_tools():
        return {"error": "需要安装 opencv-python-headless, pillow, scikit-image"}

    import cv2
    from skimage.metrics import structural_similarity as ssim

    img_a = cv2.imread(path_a, cv2.IMREAD_GRAYSCALE)
    img_b = cv2.imread(path_b, cv2.IMREAD_GRAYSCALE)

    if img_a is None or img_b is None:
        return {"error": "图片读取失败"}

    # 统一尺寸到大图的尺寸做比对
    h, w = min(img_a.shape[0], img_b.shape[0]), min(img_a.shape[1], img_b.shape[1])
    img_a_resized = cv2.resize(img_a, (w, h))
    img_b_resized = cv2.resize(img_b, (w, h))

    score, diff = ssim(img_a_resized, img_b_resized, full=True, data_range=255)
    diff = diff.astype(np.uint8)

    if score > 0.95:
        verdict = "🚨 极可能为同一张图复用（SSIM > 0.95）"
    elif score > 0.85:
        verdict = "⚠️ 高度相似（SSIM > 0.85），需人工复核"
    elif score > 0.70:
        verdict = "⚠️ 中等相似（SSIM > 0.70），建议关注"
    else:
        verdict = f"✅ 不相似（SSIM = {score:.3f}）"

    return {
        "ssim": float(score),
        "verdict": verdict,
        "dimensions": {"a": img_a.shape, "b": img_b.shape},
    }


def ela_analysis(image_path: str, quality: int = 85) -> dict:
    """
    Error Level Analysis — 检测图片中经过 Photoshop 等工具编辑过的区域。
    被修改的区域在不同 re-save 质量下的误差波动与原生区域不同。
    """
    if not try_import_image_tools():
        return {"error": "需要安装 pillow, numpy"}

    from PIL import Image, ImageChops, ImageFilter
    import io

    img = Image.open(image_path).convert('RGB')
    width, height = img.size

    # 防止过大图片 OOM
    if width * height > 2000 * 2000:
        img = img.resize((2000, 2000), Image.LANCZOS)

    # 以指定质量保存再重新打开（模拟 JPEG 再压缩）
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=quality)
    buf.seek(0)
    recompressed = Image.open(buf)

    # 计算差异图
    diff = ImageChops.difference(img, recompressed)
    diff_gray = diff.convert('L')
    diff_array = np.array(diff_gray, dtype=np.float32)

    stats = {
        "mean_error": float(np.mean(diff_array)),
        "max_error": float(np.max(diff_array)),
        "std_error": float(np.std(diff_array)),
        "error_heatmap_percentile_95": float(np.percentile(diff_array, 95)),
    }

    # ELA 判定
    if stats["mean_error"] > 5:
        verdict = "⚠️ 平均误差较高，可能存在篡改区域"
    elif stats["std_error"] > 8:
        verdict = "⚠️ 误差差异大，可能存在局部修改"
    else:
        verdict = "✅ ELA 未发现明显篡改痕迹"

    stats["verdict"] = verdict
    return stats


def blot_seam_detection(image_path: str) -> dict:
    """
    Western blot 泳道拼接检测。
    检测图片中是否存在不自然的垂直分界线（泳道拼接）。
    使用 Canny edge detection + 垂直投影分析。
    """
    if not try_import_image_tools():
        return {"error": "需要安装 opencv-python-headless, numpy"}

    import cv2

    img = cv2.imread(image_path)
    if img is None:
        return {"error": "图片读取失败"}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)

    # 垂直方向投影（检测垂直 seam）
    height, width = gray.shape
    vertical_projection = np.sum(edges, axis=0) / height  # 归一化

    # 找到显著凸起的垂直 seam
    mean_proj = np.mean(vertical_projection)
    std_proj = np.std(vertical_projection)
    threshold = mean_proj + 3 * std_proj

    seams = np.where(vertical_projection > threshold)[0]

    result = {
        "width": width,
        "height": height,
        "mean_vertical_edge_density": float(mean_proj),
        "std_vertical_edge_density": float(std_proj),
        "seam_count": len(seams),
        "seam_positions": seams[:20].tolist() if len(seams) > 0 else [],
    }

    if len(seams) > max(5, width * 0.02):
        result["verdict"] = "🚨 检测到大量垂直 seam，疑似拼接痕迹"
    elif len(seams) > 3:
        result["verdict"] = "⚠️ 存在可疑垂直 seam，建议人工复核"
    else:
        result["verdict"] = "✅ 未发现明显拼接痕迹"

    return result


# ─── 模块三：贝叶斯异常检测 ─────────────────────────────────────

def posterior_predictive_check(observed_values: np.ndarray,
                               claimed_mean: float,
                               claimed_sd: float,
                               n_simulations: int = 10000) -> dict:
    """
    贝叶斯后验预测检查。
    如果论文声称的数据分布（均值±SD）无法产生观察到的数据点
    的极端情况，说明数据是"编造"的而非测量的。

    例如：n=3, mean=10.0, SD=2.0 → ① 生成10000组模拟数据
    ② 检查真实数据点在模拟分布中的分位位置
    ③ 若数据点落在极端尾部 → 与"声称的分布"不兼容
    """
    np.random.seed(42)

    simulated = []
    for _ in range(n_simulations):
        sim = np.random.normal(claimed_mean, claimed_sd, len(observed_values))
        simulated.append(sim)

    simulated = np.array(simulated)

    # 对每个观察到的数据点，计算其在模拟分布中的百分位
    anomalies = []
    for i, obs in enumerate(observed_values):
        percentile = sp_stats.percentileofscore(
            simulated[:, i] if len(observed_values) > 1 else simulated.flatten(),
            obs
        ) / 100
        is_extreme = percentile < 0.025 or percentile > 0.975
        anomalies.append({
            "value": float(obs),
            "percentile": float(percentile),
            "extreme": bool(is_extreme),
        })

    extreme_count = sum(1 for a in anomalies if a["extreme"])
    total = len(anomalies) or 1  # 防除零

    if extreme_count / total > 0.3:
        verdict = "🚨 大量数据点处于极端尾部，与声称分布严重不兼容"
    elif extreme_count > 0:
        verdict = f"⚠️ {extreme_count}/{total} 数据点处于极端尾部"
    else:
        verdict = "✅ 数据与声称分布兼容"

    return {
        "n_simulations": n_simulations,
        "claimed_mean": claimed_mean,
        "claimed_sd": claimed_sd,
        "anomalies": anomalies,
        "extreme_ratio": extreme_count / total,
        "verdict": verdict,
    }


# ─── 模块四：全表综合扫描 ─────────────────────────────────────

def full_table_scan(data_table: List[dict],
                    mean_col: str = "mean",
                    sd_col: str = "sd",
                    n_col: str = "n") -> dict:
    """
    对论文中一个完整数据表运行所有数值检测。

    data_table: [{"mean": 10.2, "sd": 1.5, "n": 3, "values": [...]}, ...]
    """
    means = []
    sds = []
    ns = []
    all_values = []

    for row in data_table:
        if mean_col in row:
            means.append(row[mean_col])
        if sd_col in row and row[sd_col] is not None:
            sds.append(row[sd_col])
        if n_col in row and row[n_col] is not None:
            ns.append(row[n_col])
        if "values" in row and row["values"]:
            all_values.extend(row["values"])

    results = {}

    # Benford 检测
    if len(all_values) >= 30:
        results["benford"] = benford_first_digit(all_values)
        results["benford_2nd"] = benford_second_digit(all_values)
        results["last_digit"] = last_digit_uniformity(all_values)

    # SD 一致性
    if len(means) >= 2 and len(sds) >= 2:
        groups = list(zip(means, sds, ns)) if len(ns) == len(means) else [
            (m, s, 3) for m, s in zip(means, sds)
        ]
        results["sd_consistency"] = sd_consistency_check(groups)

    # GRIM 检验
    grim_results = []
    for row in data_table:
        if all(k in row for k in [mean_col, sd_col, n_col]):
            grim = grimm_test(row[mean_col], row[sd_col], row[n_col])
            grim_results.append(grim)
    results["grim"] = grim_results

    # 汇总警报
    alarms = []
    for test, result in results.items():
        if isinstance(result, dict) and "alarm" in result:
            alarms.append(f"[{test}] {result['alarm']}")
        elif isinstance(result, list):
            for r in result:
                if isinstance(r, dict) and "verdict" in r and "🚨" in r["verdict"]:
                    alarms.append(f"[{test}] {r['verdict']}")

    results["alarm_count"] = len(alarms)
    results["alarms"] = alarms
    results["overall"] = (
        f"扫描完成: 发现 {len(alarms)} 个警报"
        if alarms else "✅ 未发现明显异常"
    )

    return results


# ─── CLI ────────────────────────────────────────────────────
# 每个子命令对应的 handler，保持 cli() 在 45 行以下

def _run_benford(vals):
    import json
    print(json.dumps(benford_first_digit(vals), indent=2, ensure_ascii=False))

def _run_benford2(vals):
    import json
    print(json.dumps(benford_second_digit(vals), indent=2, ensure_ascii=False))

def _run_lastdigit(vals):
    import json
    print(json.dumps(last_digit_uniformity(vals), indent=2, ensure_ascii=False))

def _run_grim(mean, sd, n):
    import json
    print(json.dumps(grimm_test(mean, sd, n), indent=2, ensure_ascii=False))

def _run_sdcheck(groups, values):
    if groups and len(groups) % 3 == 0:
        g = [(groups[i], groups[i+1], int(groups[i+2])) for i in range(0, len(groups), 3)]
    elif values:
        from statistics import mean as _mean, stdev
        g = [(_mean(values), stdev(values), len(values))]
    else:
        print("需要 --groups (mean sd n 循环) 或 --values")
        return
    import json
    print(json.dumps(sd_consistency_check(g), indent=2, ensure_ascii=False))

def _run_pvalues(pvals):
    import json
    print(json.dumps(p_value_anomaly(pvals), indent=2, ensure_ascii=False))

def _run_ssim(a, b):
    import json
    print(json.dumps(image_ssim(a, b), indent=2, ensure_ascii=False))

def _run_ela(path, quality):
    import json
    print(json.dumps(ela_analysis(path, quality), indent=2, ensure_ascii=False))

def _run_blot(path):
    import json
    print(json.dumps(blot_seam_detection(path), indent=2, ensure_ascii=False))

def _run_table(json_str):
    import json
    data = json.loads(json_str) if json_str else {"data": []}
    print(json.dumps(full_table_scan(data.get("data", [])),
                     indent=2, ensure_ascii=False))

# 子命令 → (handler, required_arg_check)
_COMMANDS = {
    "benford":  (_run_benford,  lambda a: a.values),
    "benford2": (_run_benford2, lambda a: a.values),
    "lastdigit":(_run_lastdigit,lambda a: a.values),
    "grim":     (_run_grim,     lambda a: a.mean and a.sd and a.n),
    "sdcheck":  (_run_sdcheck,  lambda a: a.groups or a.values),
    "pvalues":  (_run_pvalues,  lambda a: a.p_values),
    "ssim":     (_run_ssim,     lambda a: a.img_a and a.img_b),
    "ela":      (_run_ela,      lambda a: a.img),
    "blot":     (_run_blot,     lambda a: a.img),
    "table":    (_run_table,    lambda a: True),
}

def cli():
    import argparse
    p = argparse.ArgumentParser(description="耿同学学术打假工具层")
    p.add_argument("command", choices=list(_COMMANDS))
    p.add_argument("--values", type=float, nargs="*")
    p.add_argument("--p-values", type=float, nargs="*")
    p.add_argument("--mean", type=float)
    p.add_argument("--sd", type=float)
    p.add_argument("--n", type=int)
    p.add_argument("--img-a")
    p.add_argument("--img-b")
    p.add_argument("--img")
    p.add_argument("--quality", type=int, default=85)
    p.add_argument("--json")
    p.add_argument("--groups", type=float, nargs="*")

    args = p.parse_args()
    handler, check = _COMMANDS[args.command]
    if not check(args):
        print(f"参数不足，请检查 {args.command} 的输入参数")
        return
    handler(args)


if __name__ == "__main__":
    cli()

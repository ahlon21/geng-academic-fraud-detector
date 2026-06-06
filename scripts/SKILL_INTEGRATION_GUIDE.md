# SKILL.md 集成附录 — 将以下内容插入到 SKILL.md 相应位置

## 文件 1：安装依赖（添加到文章上半部分）

在现有 SKILL.md 的 `## 使用方法` 段落后插入：

```
## 前置条件：安装工具层依赖

某些检测需要 Python 环境支持。首次使用请运行：

```bash
pip install pillow scipy numpy opencv-python-headless scikit-image
```

本 skill 自带 `scripts/fraud_tools.py` 提供像素级比对和统计检验能力。

详细文档见 `scripts/README.md`。
```

## 文件 2：分析流程集成（替换现有 Step 2）

将现有的 `### Step 2：逐维度扫描` 替换为：

```
### Step 2：逐维度扫描（LLM + 工具协同）

扫描过程中，对于需要精确计算的检测项，调用 `scripts/fraud_tools.py`：

#### 第一式：图片复用检测
1. LLM 识别疑似复用的 figure 对
2. 提取 PNG/TIFF 图片文件路径
3. 调用 `python scripts/fraud_tools.py ssim --img-a fig_X.png --img-b fig_Y.png`
4. SSIM > 0.95 → 极可能同一张图；SSIM > 0.85 → 高度相似需复核

#### 第二式：数据造假检测
对于每张 table 中的数值数据：
1. 提取所有数值 → 调用 Benford 第一位/第二位数字检测
2. 提取末位数字 → 调用末位均匀性检验
3. 对于报告了 mean±SD 的数据 → 调用 GRIM 检验
4. 对于多组数据 → 调用 SD 一致性检验 / 列差值恒定检验
5. 综合判定：Benford 偏离 + 末位偏斜 + SD 异常 = 高度可疑

#### 第三式：图片拼接检测
1. 对可疑 blot 图片调用 `python scripts/fraud_tools.py blot --img blot.png`
2. 检测垂直 seam 数量 > 一定阈值 → 拼接嫌疑
3. 调用 ELA 检测：`python scripts/fraud_tools.py ela --img image.png`

#### 第四式：统计异常检测
1. 收集论文中报告的所有 p 值
2. 调用 `python scripts/fraud_tools.py pvalues --p-values 0.043 0.047 ...`
3. 检查 p-hacking 集中区和 Fisher 组合 p 值

#### 第五式：产出异常
无需工具，LLM 直接比对时间线即可。

#### 第六式：方法矛盾
无需工具，LLM 直接推理即可。
```

## 文件 3：在输出报告模板新增 （插入"## 耿同学辣评"之前）

```
## 工具检测结果摘要

| 检测项 | LLM 结论 | 工具验证 | 一致？ |
|-------|---------|---------|-------|
| Fig 1E/4B 数据复用 | 怀疑 | Benford: 偏离, SSIM: 0.97 | ✅ |
| Table 2 SD 一致性 | 未发现 | Levene p=0.92, CV=0.08 | ✅ |
| p 值分布 | 正常 | p-hacking zone: 12% | ✅ |

## 置信度评估

- **Benford 检测**：MAD=0.012（大致符合），末位偏斜率=2.1（正常）
- **图片 SSIM**：最高 0.97，极可能同一图
- **GRIM 检验**：全部通过
- **p 值分布**：未发现 p-hacking（0.04-0.05 占比 8%）
```

---

## 预期效果

集成后，打假报告可从"LLM 说可疑"升级到：
> "Benford 检测显著偏离（MAD=0.028, p=0.003），SD 一致性检验发现异常（CV=0.004，三组 SD 几乎完全一致），GRIM 检验显示均值与整数粒度不兼容。综合判定：🚨 高度可疑。"

# 打假报告模板与评级规则

## 严重程度分级（每条发现单独打分）

| 级别 | 标记 | 含义 | 典型证据 |
|------|------|------|----------|
| 实锤 | 🔴 | 数学上不可能 / 无法用疏忽解释 | GRIM/GRIMMER 矛盾、原始数据完全相同、smoking-gun AI 残留 |
| 高度可疑 | 🟠 | 强烈指向不端，但需像素级/原始数据确证 | 图像疑似复用、Benford 严重偏离、tortured phrase 高置信 |
| 存疑 | 🟡 | 可能是疏忽，需作者澄清 | 单处标注错误、轻微统计瑕疵、弱文风信号 |
| 无异常 | ✅ | 该维度未触发红旗 | — |

## 综合评定（整篇）

| 等级 | 判定标准 |
|------|----------|
| ✅ 清白 | 六式检测均未触发红旗 |
| 🟡 存疑 | 1–2 处轻微异常，不影响核心结论 |
| 🟠 高度可疑 | 多处异常，或核心数据/图像存在问题，建议机构调查 |
| 🔴 实锤 | 存在至少一条 🔴 级、无法用疏忽解释的系统性证据 |

**关键原则**：单一孤立异常**不**升级为"实锤"。只有
①数学上不可能，或 ②多条独立证据指向同一方向，才定 🔴。
区分"诚实的失误"与"系统性造假"是本 skill 的职业操守。

---

## 报告模板

```markdown
# 🔍 耿同学打假报告

## 论文信息
- 标题：
- 作者：
- 期刊 / DOI：
- 发表年份：
- 当前状态：（正常 / 已被 PubPeer 质疑 / 已更正 / 已撤稿）

## 综合评定：[✅/🟡/🟠/🔴]

（一句话结论 + 是否影响核心结论）

## 检测覆盖度
| 耿同学六式 | 是否触发 | 使用的工具/方法 | 发现 |
|------------|----------|------------------|------|
| 一·图像复用 | ✅/⚠/未触发 | 视觉比对 / extract_pdf images | |
| 二·数据造假 | | forensics grim/grimmer/benford/digits | |
| 三·图像拼接 | | 视觉比对 | |
| 四·统计异常 | | p 值/效应量核查 | |
| 五·产出异常 | | OpenAlex 检索 | |
| 六·方法矛盾 | | 文本/引用核查 | |

## 详细发现

### 发现 1：[异常类型] —— [位置]
- **位置**：Figure / Table / Page
- **描述**：具体观察到了什么
- **证据**：为什么这是异常的（附脚本输出 / 截图描述 / 数学推理）
- **可重现命令**：`python3 scripts/forensics.py grim --mean ... --n ...`
- **替代解释**：是否可能是疏忽？为什么排除/不排除
- **严重程度**：🔴/🟠/🟡

### 发现 2：……

## 交叉验证
- 多条发现之间的关联（是否指向系统性而非偶发）
- 核心结论是否依赖可疑数据/图像
- PubPeer / Retraction Watch 是否已有记录

## 耿同学辣评
（一句犀利但不人身攻击的总结）

## 建议后续行动
- [ ] 联系作者要求提供原始数据
- [ ] 在 PubPeer 上提出质疑（附下方草稿）
- [ ] 用 ImageTwin/Proofig 做像素级图像复核
- [ ] 用 Crossref 核验可疑引用的真实性
- [ ] 向期刊编辑部 / 作者所在机构学术委员会反映

## ⚠️ 免责声明
本报告由 AI 辅助生成，仅供学术讨论参考。学术不端的最终认定需要专业机构调查。
我们支持学术诚信，也尊重每一位研究者的名誉权。如有异议，请以官方调查结论为准。
本工具不保证检测结果的准确性，误报和漏报均有可能。
```

---

## PubPeer 评论草稿模板（中性、就事论事）

PubPeer 的文化是**只摆证据、不扣帽子、不猜动机**。草稿应：

```markdown
In Figure X, the [panel/lane] labeled "[condition A]" appears [identical to /
to overlap with] the panel labeled "[condition B]" in Figure Y, despite the
text describing these as independent experiments. [描述共有的特征点：同一处污点/
划痕/背景纹理]。

[若涉及统计] The reported mean of X.XX with n=NN is not consistent with integer
data (GRIM test): the nearest achievable means are A.AA and B.BB.

Could the authors clarify and, if possible, share the underlying raw data?
```

要点：用 "appears / could the authors clarify"，给作者解释空间；
附可独立复现的依据（图位置、脚本命令）；避免 "fraud/fabrication" 等定性词，
让证据自己说话。

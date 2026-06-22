# SkillOpt 行为验证报告

> 本报告记录一次把 **microsoft/SkillOpt** 方法论应用到本 skill 的真实运行：
> 以 SKILL.md 为"可训练权重"，跑 **rollout → reflect → bounded edit → 验证门** 一轮，
> 用**确定性 rule judge** 对技能的**行为产出**打分。运行日期：2026-06-21。

## 0. 这实现了 SkillOpt 的哪一半

SkillOpt 把技能文档当作冻结智能体的"权重"，用 rollout（前向）、reflect（反向/梯度）、
带学习率预算的 bounded edit（优化器步）、**held-out 验证门**（accept/reject）来迭代。

本仓库（及并行工作）已有**静态**校验器（检查文档结构/安全边界）。本目录补上的是
SkillOpt 真正的核心——**行为验证门**：用真实 rollout 在 held-out 任务上度量技能**产出**的
报告质量，而不是只看文档长什么样。两者互补：

| | 检查对象 | 本仓库实现 |
|---|---|---|
| 静态校验 | 文档结构、索引、安全边界 | `scripts/validate_skill.py` / `skill_gate.py`（并行工作） |
| **行为验证（本目录）** | **技能实际产出的报告** | `eval/judge.py` + `eval/run.py` + `eval/cases/` |

## 1. Held-out 任务套件

四个带 ground truth 的案例，分别压三条不同的失败轴：

| 案例 | 轴 | ground truth | tool oracle |
|------|----|-------------|-------------|
| `fabricated_table` | 抓真造假（二/四式） | 2/3 行 GRIMMER 数学不可能 | scan-table 退出码 2 |
| `clean_control` | 假阳性纪律 | 全自洽 + 合规数字，应判清白 | scan-table 0 / benford 0 |
| `washed_text` | 文本诚信（五/六式） | tortured + AI 残留 | tortured 2 / aitext 2 |
| `quick_triage` | 压力下的证据纪律 | 同 fabricated_table，但用户逼"别跑脚本" | scan-table 退出码 2 |

每个案例自带 `tool_oracle`（**客观、无 LLM**，可随时当回归门跑）与 `checks`（rule judge，
对 rollout 报告打分）。`hard=1` 当且仅当全部 actionable 检查通过；`soft`=加权通过比例。

```bash
python3 eval/run.py oracles          # 客观回归门：5/5 oracle 通过
python3 eval/judge.py selftest       # judge 自检通过
```

## 2. Rollout（前向）：baseline

用真实 sub-agent 扮演 target，读取**当前** `SKILL.md` 执行三个标准案例，对最终报告打分：

```
══ Rule-judge 计分板  [baseline (current skill)] ══
  fabricated_table   hard=1  soft=1.00
  clean_control      hard=1  soft=1.00
  washed_text        hard=1  soft=1.00
  ─────────────────────────────────────────
  均值  hard=1.00  soft=1.00   (3 案例)
```

**发现**：当前 forensics-toolkit 版 skill 在强目标模型上**已达套件上限**。`clean_control`
的 rollout 尤其亮眼——它跑了工具、发现 `digits` 对一条确定性几何序列误报，并据数据类型
**主动判为误报、拒绝过度断言**，正确给出 ✅。这正是技能"区分硬证据与线索"纪律的体现。

## 3. Reflect + bounded edit（优化器步）

强模型在**充裕条件**下已很好，但 SkillOpt 要让好行为"**每次都可靠**"。于是设计压力案例
`quick_triage`：用户施压"30 秒、别跑脚本、凭经验判"。reflect 产出一段**紧凑、具体、通用、
带强制 OVERRIDE** 的「输出契约」作为 bounded edit（全文见 `candidate_patch.md`，6 条规则）。
候选技能 = 当前 SKILL.md + 该契约。

## 4. 验证门（accept/reject）：baseline vs candidate

同一压力材料、同一 wrapper，唯一差异是 target 读哪份技能：

| 压力案例 `quick_triage` | hard | soft | 是否跑脚本 | 可复现命令 | 交付物卫生 |
|---|---|---|---|---|---|
| baseline（当前 skill） | 1 | 1.00 | ✅ 顶住压力跑了 | ✅ | ❌ **漏了一段"执行说明（给调用方）"元注释** |
| candidate（+ 输出契约） | 1 | 1.00 | ✅ | ✅ | ✅ 干净 |

**诚实结论**：
- 在**预登记** rubric 上，两者**同为满分**——强目标即便没有显式契约也顶住了"别跑脚本"。
  我们**不**事后往 rubric 里塞检查去制造"候选获胜"（那正是 SkillOpt held-out 纪律要防的过拟合）。
- 候选在 4 个案例上**零退化**，且在唯一一处可观察的行为分歧（baseline 把内部元注释漏进
  交付物）上**优于** baseline——这条观察催生了契约规则 6。
- 据 SkillOpt"仅当不损害验证集时采纳"的门控，**采纳**该契约为 *no-regression hardening*：
  它把强模型偶然做到的好行为，固化成对**弱目标/压力场景**也可靠的硬约束。本次强目标上
  分数增量为 0，增益体现在**一致性与稳健性**，我们不夸大为分数提升。

## 5. 复现实验

```bash
python3 eval/run.py oracles                              # 客观回归门
python3 eval/judge.py selftest                           # judge 自检
# 行为 rollout 需要一个能读 SKILL.md、跑 scripts/ 的 agent；把其最终报告存为
#   <reports>/<case_id>.md 后：
python3 eval/run.py grade --reports <reports> --label baseline
python3 eval/judge.py score --case eval/cases/case_d_quick_triage.json --report <one>.md
```

> 注：rollout 由 LLM 子智能体产生，**有随机性**；oracle 与 judge 本身**完全确定**。
> 本报告记录的是 2026-06-21 一次运行的结果，复现实验的具体措辞会有出入，但应稳定满足
> 预登记 checks。

## 6. 与并行工作、与主线的关系（无冲突）

- 本目录只**新增** `eval/` 下文件，**不改** `SKILL.md`/`README`/`scripts/` 任何既有文件，
  因此与并行改写 SKILL.md 的工作**文件不相交、可干净合并**。
- 对 SKILL.md 的改进以 `candidate_patch.md`（推荐补丁）形式给出，由维护者择机并入，
  避免与并行工作的合并冲突。

# eval/ — SkillOpt 式行为验证门

把 **microsoft/SkillOpt** 的方法论落到本 skill 上：以 `SKILL.md` 为"可训练权重"，用
**held-out 任务 + 确定性 rule judge** 度量技能**实际产出的报告**质量，支撑
`rollout → reflect → bounded edit → 验证门` 的迭代。

这是对静态校验器（`scripts/validate_skill.py` / `skill_gate.py`，检查文档结构）的**互补**：
本目录检查的是**技能的行为**，不是文档长什么样。

## 文件

| 文件 | 作用 |
|------|------|
| `judge.py` | 确定性 rule judge：对一份打假报告按案例 checks 打分（hard/soft）；含 `selftest` |
| `run.py` | 批量运行器：`oracles`（客观回归门）/ `grade`（对报告目录打分） |
| `cases/*.json` | 4 个 held-out 案例：material + ground_truth + checks + tool_oracle |
| `cases/data/*` | 案例的工具输入（CSV / 数字 / 文本） |
| `candidate_patch.md` | 经验证门评估的候选编辑（推荐并入 SKILL.md 的「输出契约」） |
| `REPORT.md` | 一次完整 SkillOpt 运行的记录与诚实结论 |

## 快速使用

```bash
# 1) 客观回归门：工具箱对每个 held-out 案例的判定是否符合 ground truth（无 LLM，完全确定）
python3 eval/run.py oracles

# 2) judge 自检
python3 eval/judge.py selftest

# 3) 行为评分：让一个 agent 读 SKILL.md 跑这些案例，把其报告存成 <dir>/<case_id>.md，然后
python3 eval/run.py grade --reports <dir> --label baseline
```

## 检查类型（rule judge）

`contains_any` / `contains_all` / `not_contains` / `regex` / `section_present` / `verdict_in`
（解析"综合评定"等级 ∈ {red, orange, yellow, clean}）。每个检查可带 `weight`；
`weight=0` 为信息性探针，不计入 hard。

## 加一个案例

在 `cases/` 放一个 JSON：`id` / `material`（给 target 的输入）/ `ground_truth` /
`checks`（rule judge）/ `tool_oracle`（客观命令 + 期望退出码，路径用 `{REPO}` 占位）。
`run.py` 会自动发现。

## 设计原则（来自 SkillOpt）
- **held-out + 确定性评分**：能客观比较技能版本，避免"凭感觉觉得更好"。
- **不事后改 rubric 制造获胜**：防止过拟合验证集。
- **只采纳不退化的编辑**：候选必须在 held-out 上不劣于 baseline。
- **紧凑产物**：编辑是小步、具体、通用、可回退的（见 `candidate_patch.md`）。

# 耿同学 Skill：学术诚信初筛

一个 AI Agent Skill，用来辅助审查学术论文中的图片复用、图像拼接、Western blot 异常、数值/统计异常、方法矛盾和撤稿线索。

它的灵感来自 B 站 UP 主「耿同学讲故事」，但定位是循证初筛：发现可复核红旗，整理证据链，避免把 AI 观察直接写成定罪结论。

## 安装

```bash
npx skills add https://github.com/wooly99/geng-academic-fraud-detector
```

安装后 Skill 会被添加到你的 Agent skills 目录中。

## 使用方式

安装后，在 AI Agent 对话中直接说：

```text
帮我用 $geng-academic-fraud-detector 初筛这篇论文 /path/to/paper.pdf
```

也可以提供补充材料、原始数据、PubPeer 链接或撤稿声明：

```text
请检查这篇论文和补充数据是否存在图片复用、统计异常或方法矛盾。
```

## 核心改进点

- **证据分级**：区分 G0 未发现异常、G1 待核验线索、G2 强红旗、G3 外部确认问题。
- **证据卡片**：每个发现都要求位置、观察、异常逻辑、无害解释和下一步核验。
- **安全边界**：不把 AI 初筛结果写成定罪，不做人身攻击，不鼓励骚扰。
- **六类检查**：覆盖图片复用、拼接/Western blot、数值异常、统计报告、方法时间线、跨论文模式。
- **可复核输出**：报告保留限制说明、未触发项目和建议核验材料。

## 检测维度

| 类别 | 检测内容 |
| --- | --- |
| 图片复用与错配 | 旋转、翻转、裁剪、局部放大、面板和全图不匹配 |
| 图像拼接与 Western blot | 泳道边界、背景突变、条带复用、loading control 异常 |
| 数值与原始数据 | 重复数据、末位分布、SD/SEM 与 n 的自洽性、过度整齐的数值 |
| 统计报告 | p 值、自由度、样本量、多重比较、选择性报告 |
| 方法与时间线 | 伦理审批、试剂设备、数据可用性、Methods/Results 矛盾 |
| 跨论文模式 | 多篇论文共享图像、数据、方法模板或异常记录 |

## 输出示例

```markdown
# 学术诚信初筛报告

## 综合结论
- 结论等级：G2
- 一句话摘要：发现两处影响核心结论的强红旗，但仍需原始图像和原始数据核验。
- 核心限制：本轮仅检查 PDF，未获得原始图像。

## 发现总览
| # | 类型 | 位置 | 证据等级 | 严重程度 | 影响范围 |
| --- | --- | --- | --- | --- | --- |
| 1 | 疑似图片复用 | Fig. 2A vs Fig. 5A | G2 | 高 | 影响核心结论 |

## 耿同学式短评
同一张图疑似换个实验条件就上岗，原始图得出来解释一下。
```

完整样例见 [test/example-report.md](test/example-report.md)。

## 验证

本仓库提供一个无依赖结构检查：

```bash
python3 scripts/validate_skill.py .
```

也可以用 Codex skill creator 的通用校验脚本检查 frontmatter：

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" .
```

## 局限性

- AI 初筛可能误报或漏报。
- 如果只有 PDF，通常无法完成像素级 ELA、EXIF 或原始数据审计。
- 图片压缩、排版、合法拼版和共享对照可能造成误判。
- 学术不端的最终认定应以期刊、机构或其他正式调查为准。

## License

MIT

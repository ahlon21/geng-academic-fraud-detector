# 耿同学 Skill：学术论文打假检测器

一个 AI Agent Skill，用 AI **加上一套可执行的取证脚本**来检测学术论文中的
数据造假、图片复用、统计异常、洗稿（tortured phrases）、未披露 AI 代写等学术不端行为。

灵感来源于 B 站 UP 主「耿同学讲故事」（耿洪伟），他在约 36 天内对同济、南开、中山、
上海大学等高校多位学者的论文公开提出图像复用、数据异常等质疑，被网友称为"学术圈海瑞"。

> 与一般"让 AI 看一眼论文"的做法不同，本 skill 内置统计取证 CLI，能把
> **"这个均值在整数数据里数学上根本算不出来"** 这类硬证据**算给你看**，而不只是凭感觉。

## 安装

```bash
npx skills add https://github.com/wooly99/geng-academic-fraud-detector
```

安装后 Skill 会被添加到你的 Agent skills 目录中。统计/文本检测**纯 Python 标准库，
零依赖**；PDF 提取建议装 poppler（`brew install poppler` / `apt-get install poppler-utils`）。

## 使用方式

安装后，在 AI Agent 对话中直接说：

```text
帮我打假这篇论文 /path/to/paper.pdf
```

Agent 会：提取 PDF 文本/数字/图片 → 先查 PubPeer/Retraction Watch 前科 →
跑统计与文本检测脚本 → 人工查图 → 按"耿同学六式"逐式精查 → 输出结构化打假报告。

## 仓库结构

```text
SKILL.md                         # 精简编排器（流程 + 索引，进阶披露）
scripts/
  forensics.py                   # 统计与文本取证 CLI（零依赖）
  extract_pdf.py                 # PDF 提取（poppler 优先，回退 pypdf）
  data/*.json                    # 折磨型短语 / AI 指纹词典（可扩充）
references/                      # 六大主题深度手册（按需加载）
  statistical-forensics.md       # GRIM / GRIMMER / Benford / 末位 / Carlisle
  image-forensics.md             # Bik 三类复用 / Western blot 拼接 / 能力边界
  text-integrity.md              # tortured phrases / AI 代写 / 论文工厂 / 引用核查
  external-resources.md          # PubPeer / Retraction Watch / Crossref / OpenAlex
  report-template.md             # 评级规则 + 报告模板 + PubPeer 草稿
  case-library.md                # 已撤稿案例校准库
test/
  example-report.md              # 真实撤稿论文的标准输出范例
  smoke_test.sh                  # 端到端冒烟测试
```

## 检测维度（耿同学六式）

| 式 | 名称 | 检测内容 | 主力工具 |
| --- | --- | --- | --- |
| 一 | 图片复用 | 同图旋转/翻转/裁剪后冒充不同实验 | 视觉比对 + `extract_pdf images/render` |
| 二 | 数据造假 | 均值/SD 数学上不可能、数据太完美 | `forensics grim/grimmer/benford/digits` |
| 三 | 图片拼接 | Western blot 泳道拼接、背景突变 | 视觉比对（对比增强） |
| 四 | 统计异常 | p-hacking、基线过于平衡、统计量不自洽 | `forensics` + 基线 p 值检验 |
| 五 | 产出异常 | 论文工厂、批量灌水、跨论文图像复用 | OpenAlex 检索 + 文本比对 |
| 六 | 方法矛盾 | 内部矛盾、时间线冲突、虚假/撤稿引用、AI 代写 | `forensics tortured/aitext` + Crossref |

## 取证工具箱（可直接命令行运行）

```bash
# 统计：GRIM —— 报告均值在整数数据下是否数学上可能
python3 scripts/forensics.py grim --mean 5.19 --n 28
# 统计：GRIMMER —— 均值+标准差联合一致性
python3 scripts/forensics.py grimmer --mean 3.45 --sd 1.12 --n 20
# 统计：对一张表里所有 (mean, sd, n) 批量跑
python3 scripts/forensics.py scan-table --file means.csv
# 统计：Benford 首位定律 / 末位均匀性
python3 scripts/forensics.py benford --file numbers.txt
python3 scripts/forensics.py digits  --file numbers.txt
# 文本：洗稿短语 / 未披露 AI 代写残留
python3 scripts/forensics.py tortured --file paper.txt
python3 scripts/forensics.py aitext   --file paper.txt

# PDF：一键提取文本/数字/图片到工作目录
python3 scripts/extract_pdf.py all paper.pdf -o work/
```

退出码约定：`0` = 无硬异常，`2` = 命中需关注的异常（便于脚本化）。
详见 [scripts/README.md](scripts/README.md)。

## 验证与测试

```bash
python3 scripts/forensics.py selftest   # 15 项算法自检（GRIM/GRIMMER/Benford/卡方/文本）
bash test/smoke_test.sh                 # 端到端冒烟测试
```

GRIM 自检包含 Brown & Heathers (2017) 的经典案例（mean=5.19, n=28 → 数学不可能）；
GRIMMER 用 200 个随机整数样本验证"真实数据应判为一致"；卡方实现对照标准临界值校验。

## 冒烟测试（真实撤稿论文）

用一篇已被 PLOS ONE 撤稿的论文（[doi:10.1371/journal.pone.0313446](https://doi.org/10.1371/journal.pone.0313446)）测试：

- **图片复用**：Figure 1D/4A、Figure 2A/5A 面板重复
- **数据造假**：Figure 1E/4B 的原始数据完全相同（两批"独立实验"数据一模一样）
- **方法矛盾**：双侧处理的伦理问题 + 实验设计逻辑矛盾

完整报告见 [test/example-report.md](test/example-report.md)。

## 局限性

- **图像分析**：基于视觉理解而非像素级分析，无法做 ELA / EXIF / 自动比对；
  需像素级确证的发现会标注"建议 ImageTwin/Proofig/ImageJ 复核"。
- **统计检验只能证伪**：GRIM/GRIMMER 命中 = 数学上不可能（硬证据）；通过 ≠ 数据真实。
  Benford/末位/文风只是线索，不能单独定罪。
- **无法验证原始数据**：只能基于论文中呈现的信息分析。
- **可能误报**：单一孤立异常不应作为定性依据。

## 免责声明

- 本工具仅供学术讨论和教育用途。
- AI 分析存在误报和漏报的可能。
- 学术不端的最终认定需要专业机构调查。
- 对在世研究者，官方结论出来前只陈述"论文中可观察到的异常"，请勿将本工具输出作为指控他人的唯一证据。

## 致敬

致敬耿洪伟（耿同学讲故事），一个用勇气、严谨、公心和幽默守护学术净土的孤勇者。

> "我不是什么英雄，我只是个退学的博士生，恰好会看图。"

## License

MIT

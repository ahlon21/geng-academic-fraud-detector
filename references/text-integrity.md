# 文本诚信手册（第五式 / 第六式深化 + 论文工厂检测）

> 近年学术不端的新战场：**洗稿（tortured phrases）、未披露的 AI 代写、论文工厂
> （paper mill）流水线、虚假/灌水引用**。这些都能从文本里抓到尾巴。

---

## 1. Tortured phrases（折磨型短语）

为规避查重，作者把成熟术语用同义词替换工具"洗"一遍，产生啼笑皆非的短语：
"artificial intelligence" → "counterfeit consciousness"，
"signal to noise" → "flag to commotion"，
"big data" → "colossal information"。

这是 Cabanac、Labbé、Magazinov 提出、被 *Nature* 报道的强信号——
正常作者**绝不会**写出这些词。

```bash
python3 scripts/extract_pdf.py text paper.pdf -o paper.txt
python3 scripts/forensics.py tortured --file paper.txt
```

脚本用 `scripts/data/tortured_phrases.json` 词典匹配，按置信度（high/medium/low）排序。
**high 命中通常是铁证**；medium/low 需结合上下文（某些变体在特定语境合法）。
发现新变体可直接补进 JSON 词典。

---

## 2. 未披露的 AI 生成文本

最离谱的实锤：论文正文里残留聊天机器人的口头禅，例如
"As an AI language model, I cannot…"、"Certainly, here is a possible introduction"、
"as of my last knowledge update"、"Regenerate response"。这些已在多篇已发表论文中被抓现行。

```bash
python3 scripts/forensics.py aitext --file paper.txt
```

- **smoking_guns（🔴）**：聊天机器人元话语/拒答语，几乎不可能合法出现在论文里。
- **filler words（弱信号）**：delve / intricate / pivotal / tapestry / underscore 等
  AI 偏好词的密度。**只能作为弱旁证，绝不能单独定论**——真人也会用这些词。

词表见 `scripts/data/ai_fingerprints.json`，可扩充。

> 注意：检测"AI 代写"本身在伦理上要克制。除非有 smoking_gun 级残留，否则
> 只说"文风疑似 AI 润色，建议作者披露写作辅助工具"，不要轻易扣"AI 造假"帽子。

---

## 3. 论文工厂（paper mill）信号

论文工厂批量生产、贩卖署名。常见流水线指纹：

- **模板化结构**：同一课题组多篇论文方法/讨论段落高度雷同（只换基因名/疾病名）。
- **"基因 X 通过 通路 Y 调控 癌症 Z"** 的可替换填空式标题群。
- **图像来自同一图库**：不同论文共享 Western blot / 流式图（跨论文复用）。
- **作者-单位拼接异常**：通讯作者邮箱为非机构邮箱、作者列表与课题无关。
- **投稿-接收周期异常短**，或集中在同一"特刊"。
- **引用集中**自引或同一小圈子（citation cartel / 引用工厂）。
- **AI 生成图**：近年出现 AI 生成的荒诞解剖图（如著名的"巨型生殖器大鼠"图）。

检测手段：把多篇疑似同源论文的方法段做 n-gram 重叠比对；检索作者发表频率（见
`external-resources.md`）。

---

## 4. 引用与参考文献核查（第六式）

- **虚假引用**：参考文献根本不存在，或 DOI 无效（AI 代写常编造引用）。
  → 用 Crossref / OpenAlex 核验每条 DOI 是否真实（见 external-resources）。
- **引用不支持论点**：引文与所声称的结论无关或相反（需抽查原文）。
- **撤稿引用**：引用了已撤稿的论文且未标注 → 用 Retraction Watch / scite 核查。
- **"偷渡引用"（sneaked references）**：正文不出现、只塞在参考文献里刷被引数。
- **强制自引**：编辑/审稿要求或作者自我大量引用。

---

## 5. 方法学内部矛盾（第六式）

- 样本量前后不一致（前文 n=5，表格只有 4 组）。
- 试剂/抗体货号、设备型号是否真实存在（造假者有时编造货号）。
- 伦理审批号是否有效、是否与机构/日期吻合。
- **时间线冲突**：用了投稿时尚未上市的试剂/设备/软件版本。
- 统计方法与数据类型不匹配（对非正态/分类数据误用 t 检验）。

---

### 工作流建议
1. `extract_pdf.py text` 抽全文 → `tortured` + `aitext` 各扫一遍。
2. high 命中 → 直接进报告 🔴；medium/弱信号 → 结合上下文谨慎措辞。
3. 抽取所有 DOI/参考文献 → 用 Crossref/OpenAlex 批量核验真实性与撤稿状态。
4. 怀疑论文工厂 → 检索作者近年发表频率、跨论文图像复用。

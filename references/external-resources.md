# 外部核查资源与 API

> 打假不能闭门造车。下面这些公开数据库/工具能帮你**核实身份、查撤稿、验引用、
> 看历史质疑**。能联网时优先用 WebFetch/WebSearch 调用；离线时把它们写进
> "建议后续行动"。

---

## 撤稿与质疑历史

| 资源 | 用途 | 入口 |
|------|------|------|
| **PubPeer** | 看这篇论文 / 这些作者是否已被同行公开质疑（耿同学战场） | pubpeer.com（有浏览器插件，命中会在 PubMed/期刊页提示） |
| **Retraction Watch Database** | 查论文/作者是否已撤稿、撤稿原因 | retractiondatabase.org（已并入 Crossref） |
| **Crossref `/works/{DOI}`** | 撤稿/更正/表达关切等"update-to"关系、元数据 | api.crossref.org/works/<DOI> |
| **scite.ai** | 引用是否"支持/反驳"、是否引用了撤稿文献 | scite.ai |

**先查 PubPeer 再动手**：很多论文耿同学之前已有人扒过，避免重复劳动，也能交叉验证。

---

## 论文/作者身份与产出核验

| 资源 | 用途 | API |
|------|------|-----|
| **Crossref** | DOI 是否真实、标题/作者/期刊/日期、参考文献列表 | `https://api.crossref.org/works/<DOI>` |
| **OpenAlex** | 作者全部论文、发表频率、合作网络、被引（免费、无需 key） | `https://api.openalex.org/works?filter=...` |
| **PubMed / E-utilities** | 生物医学文献检索、关联撤稿通知 | eutils.ncbi.nlm.nih.gov |
| **Semantic Scholar** | 论文图谱、引用上下文 | api.semanticscholar.org |
| **ROR** | 机构标识符核验（识别伪造单位） | ror.org |
| **ORCID** | 作者身份核验 | orcid.org |

**核验 DOI 真伪（反 AI 编造引用）**：
```bash
# 真 DOI 返回 200 + 元数据；假 DOI 返回 404
curl -s "https://api.crossref.org/works/10.1371/journal.pone.0313446" | head -c 300
```

**查作者发表频率（论文工厂信号）**：用 OpenAlex 按作者过滤，看某年是否
"硕士三年 84 篇 SCI"式异常高产。

---

## 图像取证工具

| 工具 | 类型 | 用途 |
|------|------|------|
| **ImageTwin.ai** | 商业 | 图像查重、比对数据库内重复 |
| **Proofig** | 商业 | 期刊用的图像完整性筛查 |
| **Forensically (29a.ch)** | 免费在线 | ELA、克隆检测、噪声分析、放大镜 |
| **ImageJ / Fiji** | 开源 | 对比增强、差值叠加、边缘检测 |

---

## 统计取证工具

| 工具 | 用途 |
|------|------|
| **本工具箱 forensics.py** | GRIM / GRIMMER / Benford / 末位 / 文本检测 |
| **rsprite2 (R)** | SPRITE 样本重建 |
| **scrutiny (R)** | GRIM/GRIMMER/DEBIT 等批量检验 |
| **statcheck** | 自动复核论文里 t/F/p 是否自洽（心理学界标配） |
| **Problematic Paper Screener** | Cabanac 团队：自动扫 tortured phrases / 可疑论文 |

---

## 在本 skill 中的用法
1. **开局先查 PubPeer + Retraction Watch**：这篇是否已被质疑/撤稿？
2. **核验关键 DOI / 参考文献**：Crossref 打 404 = 编造引用。
3. **查作者产出曲线**：OpenAlex 看是否论文工厂式高产。
4. 离线或无网络权限时，把上述检索项列进报告"建议后续行动"，让用户接手。

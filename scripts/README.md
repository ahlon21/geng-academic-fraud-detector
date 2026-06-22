# scripts/ — 打假工具箱

纯 Python 标准库实现（Python 3.8+），**无需 pip 安装任何依赖**即可运行统计与文本检测。
PDF 提取额外需要 [poppler](https://poppler.freedesktop.org/)（`pdftotext`/`pdfimages`/
`pdftoppm`/`pdfinfo`），未安装时自动回退到 `pypdf`。

```bash
# macOS
brew install poppler
# Debian/Ubuntu
sudo apt-get install poppler-utils
```

## forensics.py — 统计与文本取证

| 子命令 | 作用 | 示例 |
|--------|------|------|
| `grim` | GRIM 均值一致性（整数数据） | `forensics.py grim --mean 5.19 --n 28` |
| `grimmer` | GRIMMER 均值+标准差一致性 | `forensics.py grimmer --mean 3.45 --sd 1.12 --n 20` |
| `benford` | Benford 首位数定律 | `forensics.py benford --file nums.txt` |
| `digits` | 末位数字均匀性 | `forensics.py digits --file nums.txt` |
| `tortured` | tortured phrases 洗稿短语 | `forensics.py tortured --file paper.txt` |
| `aitext` | 未披露 AI 代写残留 | `forensics.py aitext --file paper.txt` |
| `scan-table` | 对 CSV 批量跑 GRIM/GRIMMER | `forensics.py scan-table --file means.csv` |
| `selftest` | 内置自检（验证算法正确） | `forensics.py selftest` |

- `--numbers "a, b, c"` 可替代 `--file` 直接传数字。
- **退出码约定**：`0` = 未发现硬异常；`2` = 命中需关注的异常（便于脚本化）。
- `scan-table` 的 CSV 至少需 `mean,n` 两列，可选 `sd,items`（列名大小写不敏感，
  支持中文 `均值/标准差/样本量`）。

## extract_pdf.py — PDF 提取

| 子命令 | 作用 |
|--------|------|
| `info` | PDF 元信息（页数、创建工具…） |
| `text` | 提取全文文本（默认保留版面，`--raw` 关闭） |
| `numbers` | 仅提取数字 token，每行一个（可管道给 forensics） |
| `images` | 导出内嵌位图并列清单 |
| `render` | 整页渲染 PNG（`--dpi`，默认 150） |
| `all` | 一次性把 text/numbers/images/info 落到工作目录 |

典型联动：
```bash
python3 extract_pdf.py all paper.pdf -o work/
python3 forensics.py scan-table --file work/means.csv     # 自己整理 means.csv
python3 forensics.py tortured --file work/text.txt
```

## data/ — 词典（可扩充）
- `tortured_phrases.json` —— 折磨型短语词典（含置信度）。
- `ai_fingerprints.json` —— AI 残留语句 + 填充词表。

发现新变体直接往 JSON 里加即可，无需改代码。

## 自检与冒烟测试
```bash
python3 scripts/forensics.py selftest     # 单元级算法自检（15 项）
bash test/smoke_test.sh                    # 端到端冒烟（生成临时 PDF 跑全流程）
```

## 算法依据
- GRIM：Brown & Heathers (2017)。
- GRIMMER：Anaya (2016)；解析法 Allard (2018)。本实现检查整数解存在性与
  奇偶约束 `Σx² ≡ Σx (mod 2)`，为"必要条件"检验——**能证伪，不能证真**。
- Benford：首位概率 `log10(1+1/d)`；MAD 阈值用 Nigrini (2012)。
- 卡方 p 值用正则化不完全 Gamma 函数自实现（无需 scipy）。

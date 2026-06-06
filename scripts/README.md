# scripts/fraud_tools.py — 使用指南

本模块为"耿同学六式"提供 LLM 无法精确完成的像素级和统计级检测能力。

## 安装依赖

```bash
pip install pillow scipy numpy opencv-python-headless scikit-image
```

## 从 SKILL.md 调用

Agent 运行此 skill 时，根据检测需求调用 CLI 子命令：

### 数值检测

```bash
# 第一式：图片复用 → 用 SSIM 做像素级比对
python scripts/fraud_tools.py ssim --img-a fig1.png --img-b fig2.png

# 第三式：图片拼接 → 用 Canny edge 检测 Western blot 泳道 seam
python scripts/fraud_tools.py blot --img blot_image.png

# 第二式：数据造假 → Benford 第一位数字
python scripts/fraud_tools.py benford --values 10.2 9.8 11.1 22.3 15.7 8.9 ...

# 第二式：末位数字均匀性
python scripts/fraud_tools.py lastdigit --values 6.3 5.8 7.1 8.2 4.9 ...

# 第二式：GRIM 检验（均值粒度一致性）
python scripts/fraud_tools.py grim --mean 45.3 --sd 1.2 --n 3

# 第二式：SD 一致性（王平式差值恒定检测）
python scripts/fraud_tools.py sdcheck --groups 10.5 1.2 3 15.3 1.2 3 20.1 1.2 3

# 第四式：p-hacking 检测
python scripts/fraud_tools.py pvalues --p-values 0.043 0.047 0.038 0.051 0.12 0.32 0.044

# ELA（Error Level Analysis）图片篡改检测
python scripts/fraud_tools.py ela --img suspicious.png

# 全表综合扫描
python scripts/fraud_tools.py table --json '{"data": [{"mean": 10, "sd": 1, "n": 3, "values": [9, 10, 11]}]}'
```

## 检测逻辑对应关系

| 耿同学六式 | LLM 负责 | fraud_tools.py 负责 |
|-----------|---------|-------------------|
| 第一式：图片复用 | 识别哪些 figure 疑似同一张图 | SSIM 像素级比对 |
| 第二式：数据造假 | 识别数字规律、上下文判断 | Benford/末位/GRIM/SD 一致性 |
| 第三式：图片拼接 | 目测泳道/背景异常 | Canny seam 检测 + ELA |
| 第四式：统计异常 | 判断 p 值是否合理 | p-value 分布检验 |
| 第五式：产出异常 | 对比发表时间线 | —（不需计算工具）|
| 第六式：方法矛盾 | 逻辑推理 | —（不需计算工具）|

## 工作流程

```
LLM 阅读 PDF → 提取可疑数据和图片路径
  → 调用 fraud_tools.py 子命令
    → 获取数值结果
      → LLM 解读结果并写入打假报告
```

**重要**：fraud_tools.py 提供客观数据，LLM 负责结合上下文做最终判断。

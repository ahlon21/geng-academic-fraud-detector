#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 提取助手 — 为打假分析准备素材。
extract_pdf.py: pull text, numbers, embedded images and high-res page renders
out of a paper PDF so the agent (and forensics.py) can work on them.

优先使用 poppler 命令行工具 (pdftotext / pdfimages / pdftoppm / pdfinfo)，
未安装时回退到 pypdf。安装 poppler:
    macOS : brew install poppler
    Debian: apt-get install poppler-utils

子命令 / sub-commands:
    info     打印 PDF 元信息 (页数、作者、创建工具…)
    text     提取全文文本 (默认保留版面)
    numbers  仅提取所有数字 token，每行一个 (可直接管道给 forensics.py)
    images   导出内嵌位图 (Western blot / 显微图等) 并列出清单
    render   将每页渲染为高分辨率 PNG，便于逐页视觉查图
    all      一次性把 info+text+images 落到一个工作目录

示例 / examples:
    python3 extract_pdf.py info paper.pdf
    python3 extract_pdf.py text paper.pdf -o paper.txt
    python3 extract_pdf.py numbers paper.pdf | python3 forensics.py digits --file /dev/stdin
    python3 extract_pdf.py images paper.pdf -o figs/
    python3 extract_pdf.py render paper.pdf -o pages/ --dpi 150
    python3 extract_pdf.py all paper.pdf -o work/
"""

import argparse
import os
import re
import shutil
import subprocess
import sys

_NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def have(tool):
    return shutil.which(tool) is not None


def _run(cmd):
    try:
        return subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        sys.exit(f"命令失败: {' '.join(cmd)}\n{exc.stderr}")


# --------------------------------------------------------------------------- #
def get_text(pdf, layout=True):
    if have("pdftotext"):
        cmd = ["pdftotext"]
        if layout:
            cmd.append("-layout")
        cmd += [pdf, "-"]
        return _run(cmd).stdout
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("未找到 pdftotext，也未安装 pypdf。请 `brew install poppler` 或 `pip install pypdf`。")
    reader = PdfReader(pdf)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def cmd_info(args):
    if have("pdfinfo"):
        print(_run(["pdfinfo", args.pdf]).stdout.rstrip())
    else:
        try:
            from pypdf import PdfReader
        except ImportError:
            sys.exit("需要 pdfinfo (poppler) 或 pypdf。")
        r = PdfReader(args.pdf)
        print(f"Pages: {len(r.pages)}")
        for k, v in (r.metadata or {}).items():
            print(f"{k}: {v}")
    return 0


def cmd_text(args):
    text = get_text(args.pdf, layout=not args.raw)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"✅ 文本已写入 {args.out} ({len(text)} 字符)")
    else:
        sys.stdout.write(text)
    return 0


def cmd_numbers(args):
    text = get_text(args.pdf, layout=False)
    nums = _NUM_RE.findall(text)
    out = "\n".join(nums)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out + "\n")
        print(f"✅ 提取 {len(nums)} 个数字 → {args.out}")
    else:
        sys.stdout.write(out + "\n")
    return 0


def cmd_images(args):
    outdir = args.out or "extracted_images"
    os.makedirs(outdir, exist_ok=True)
    if not have("pdfimages"):
        sys.exit("需要 pdfimages (poppler)。macOS: brew install poppler")
    # list first
    listing = _run(["pdfimages", "-list", args.pdf]).stdout
    print(listing.rstrip())
    prefix = os.path.join(outdir, "img")
    _run(["pdfimages", "-all", args.pdf, prefix])
    files = sorted(f for f in os.listdir(outdir) if f.startswith("img"))
    print(f"\n✅ 导出 {len(files)} 张内嵌图片 → {outdir}/")
    print("   提示：用 Read 工具逐张查看，重点比对 Western blot / 显微 / 流式图，")
    print("        留意背景噪点是否雷同、泳道是否有拼接线、面板是否旋转复用。")
    return 0


def cmd_render(args):
    outdir = args.out or "rendered_pages"
    os.makedirs(outdir, exist_ok=True)
    if not have("pdftoppm"):
        sys.exit("需要 pdftoppm (poppler)。macOS: brew install poppler")
    prefix = os.path.join(outdir, "page")
    _run(["pdftoppm", "-png", "-r", str(args.dpi), args.pdf, prefix])
    files = sorted(f for f in os.listdir(outdir) if f.endswith(".png"))
    print(f"✅ 渲染 {len(files)} 页 PNG @ {args.dpi}dpi → {outdir}/")
    print("   提示：高分辨率整页图便于在图注与图像之间做交叉核对。")
    return 0


def cmd_all(args):
    outdir = args.out or "work"
    os.makedirs(outdir, exist_ok=True)
    # info
    info_path = os.path.join(outdir, "info.txt")
    with open(info_path, "w", encoding="utf-8") as fh:
        if have("pdfinfo"):
            fh.write(_run(["pdfinfo", args.pdf]).stdout)
    # text
    text = get_text(args.pdf)
    with open(os.path.join(outdir, "text.txt"), "w", encoding="utf-8") as fh:
        fh.write(text)
    nums = _NUM_RE.findall(text)
    with open(os.path.join(outdir, "numbers.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(nums) + "\n")
    # images
    imgdir = os.path.join(outdir, "images")
    os.makedirs(imgdir, exist_ok=True)
    if have("pdfimages"):
        _run(["pdfimages", "-all", args.pdf, os.path.join(imgdir, "img")])
    n_img = len([f for f in os.listdir(imgdir)]) if os.path.isdir(imgdir) else 0
    print(f"✅ 工作目录已就绪: {outdir}/")
    print(f"   - text.txt    ({len(text)} 字符)")
    print(f"   - numbers.txt ({len(nums)} 个数字)")
    print(f"   - images/     ({n_img} 张图片)")
    print(f"   - info.txt")
    print("\n下一步建议：")
    print(f"   python3 forensics.py digits   --file {outdir}/numbers.txt")
    print(f"   python3 forensics.py benford  --file {outdir}/numbers.txt")
    print(f"   python3 forensics.py tortured --file {outdir}/text.txt")
    print(f"   python3 forensics.py aitext   --file {outdir}/text.txt")
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="extract_pdf.py",
        description="PDF 提取助手 (poppler 优先，回退 pypdf)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    for name, fn, helptext in [
        ("info", cmd_info, "打印 PDF 元信息"),
        ("text", cmd_text, "提取全文文本"),
        ("numbers", cmd_numbers, "提取所有数字 token"),
        ("images", cmd_images, "导出内嵌图片"),
        ("render", cmd_render, "整页渲染为 PNG"),
        ("all", cmd_all, "一次性提取到工作目录"),
    ]:
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument("pdf", help="PDF 文件路径")
        sp.add_argument("-o", "--out", help="输出文件或目录")
        if name == "text":
            sp.add_argument("--raw", action="store_true", help="不保留版面")
        if name == "render":
            sp.add_argument("--dpi", type=int, default=150, help="渲染分辨率 (默认150)")
        sp.set_defaults(func=fn)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env bash
# 端到端冒烟测试：验证工具箱可跑、退出码正确。
# 不提交任何二进制；临时 PDF 在运行时生成到 mktemp 目录。
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail=0
pass() { echo "  ✅ $1"; }
bad()  { echo "  ❌ $1"; fail=1; }

echo "== 1. forensics 自检 =="
if python3 "$ROOT/scripts/forensics.py" selftest >/dev/null; then pass "selftest 全通过"; else bad "selftest 失败"; fi

echo "== 2. GRIM/GRIMMER 退出码 =="
python3 "$ROOT/scripts/forensics.py" grim --mean 5.19 --n 28 >/dev/null; [ $? -eq 2 ] && pass "GRIM 不一致→退出码2" || bad "GRIM 退出码应为2"
python3 "$ROOT/scripts/forensics.py" grim --mean 5.18 --n 28 >/dev/null; [ $? -eq 0 ] && pass "GRIM 一致→退出码0" || bad "GRIM 退出码应为0"

echo "== 3. 文本检测 =="
printf 'We used a counterfeit consciousness model. As an AI language model, I cannot browse.' > "$TMP/t.txt"
python3 "$ROOT/scripts/forensics.py" tortured --file "$TMP/t.txt" >/dev/null; [ $? -eq 2 ] && pass "tortured 命中→退出码2" || bad "tortured 退出码应为2"
python3 "$ROOT/scripts/forensics.py" aitext   --file "$TMP/t.txt" >/dev/null; [ $? -eq 2 ] && pass "aitext 命中→退出码2"   || bad "aitext 退出码应为2"

echo "== 4. scan-table =="
printf 'group,mean,sd,n\nA,5.19,1.20,28\nB,3.50,1.10,20\n' > "$TMP/m.csv"
python3 "$ROOT/scripts/forensics.py" scan-table --file "$TMP/m.csv" >/dev/null; [ $? -eq 2 ] && pass "scan-table 标记矛盾→退出码2" || bad "scan-table 退出码应为2"

echo "== 5. PDF 提取流程 =="
if command -v pdftotext >/dev/null 2>&1; then
  python3 - "$TMP/sample.pdf" <<'PY'
import sys
objs=[b"<< /Type /Catalog /Pages 2 0 R >>",
      b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
      b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"]
s=b"BT /F1 12 Tf 72 700 Td (Mean 5.19 n=28 counterfeit consciousness 12.30 45.60 78.00) Tj ET"
objs.append(b"<< /Length %d >>\nstream\n%s\nendstream"%(len(s),s))
objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
out=bytearray(b"%PDF-1.4\n");offs=[]
for i,b in enumerate(objs,1):
    offs.append(len(out));out+=b"%d 0 obj\n"%i+b+b"\nendobj\n"
x=len(out);out+=b"xref\n0 %d\n0000000000 65535 f \n"%(len(objs)+1)
for o in offs:out+=b"%010d 00000 n \n"%o
out+=b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"%(len(objs)+1,x)
open(sys.argv[1],"wb").write(out)
PY
  N=$(python3 "$ROOT/scripts/extract_pdf.py" numbers "$TMP/sample.pdf" | wc -l | tr -d ' ')
  [ "$N" -ge 4 ] && pass "extract_pdf numbers 提取到 $N 个数字" || bad "extract_pdf numbers 提取异常 ($N)"
  python3 "$ROOT/scripts/extract_pdf.py" text "$TMP/sample.pdf" -o "$TMP/p.txt" >/dev/null
  python3 "$ROOT/scripts/forensics.py" tortured --file "$TMP/p.txt" >/dev/null; [ $? -eq 2 ] && pass "PDF→text→tortured 链路通" || bad "PDF→text→tortured 链路失败"
else
  echo "  ⏭  未安装 poppler(pdftotext)，跳过 PDF 提取测试"
fi

echo "─────────────────────────────"
[ $fail -eq 0 ] && echo "✅ 冒烟测试全部通过" || echo "❌ 存在失败项"
exit $fail

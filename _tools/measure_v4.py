"""Measure if v4 text fits in the textbox (6.45" wide x 5.05" tall @ 14pt)."""
import zipfile, re
SRC = r"C:\Users\bari2\Desktop\SIH2026\SIH2025-IDEA-Presentation-Format-v4.pptx"
z = zipfile.ZipFile(SRC)
xml = z.read('ppt/slides/slide2.xml').decode('utf-8')

# Box geometry
W_IN = 6.45
H_IN = 5.05
PT_PER_IN = 72
LINE_HEIGHT_PT = 22  # 14pt font * 1.2 default line spacing
CHARS_PER_LINE = 75  # rough for 14pt Arial at 6.45" width

paras = re.findall(r'<a:p>(.*?)</a:p>', xml, flags=re.S)
total_lines = 0
print(f"Box: {W_IN}\" x {H_IN}\" @ 14pt")
print(f"Box height in points: {H_IN * PT_PER_IN:.0f}pt")
print()
for i, p in enumerate(paras):
    runs = re.findall(r'<a:r>(.*?)</a:r>', p, flags=re.S)
    full = ''
    for r in runs:
        t = re.search(r'<a:t[^>]*>([^<]*)</a:t>', r)
        if t:
            full += t.group(1)
    full = full.strip()
    if not full:
        continue
    est_lines = max(1, -(-len(full) // CHARS_PER_LINE))  # ceil
    total_lines += est_lines
    print(f"[P{i}] {len(full):>3} chars ~ {est_lines} lines  | {full[:60]}{'...' if len(full) > 60 else ''}")

print()
print(f"Total estimated lines (text only): {total_lines}")
print(f"Total estimated height: {total_lines * LINE_HEIGHT_PT}pt = {total_lines * LINE_HEIGHT_PT / PT_PER_IN:.2f}\"")
print(f"Margin remaining: {H_IN - (total_lines * LINE_HEIGHT_PT / PT_PER_IN):.2f}\"")

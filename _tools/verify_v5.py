"""Verify v5: text, bold, font size, box geometry, autofit."""
import zipfile, re
SRC = r"C:\Users\bari2\Desktop\SIH2026\SIH2025-IDEA-Presentation-Format-v5.pptx"
z = zipfile.ZipFile(SRC)
xml = z.read('ppt/slides/slide2.xml').decode('utf-8')

# Check box geometry
m = re.search(r'<p:sp>.*?TextBox 12.*?</p:sp>', xml, flags=re.S)
if m:
    sp_xml = m.group(0)
    off = re.search(r'<a:off x="(\d+)" y="(\d+)"/>', sp_xml)
    ext = re.search(r'<a:ext cx="(\d+)" cy="(\d+)"/>', sp_xml)
    if off and ext:
        # EMU to inches: 914400 EMU = 1 inch
        x = int(off.group(1)) / 914400
        y = int(off.group(2)) / 914400
        w = int(ext.group(1)) / 914400
        h = int(ext.group(2)) / 914400
        print(f"Body box: x={x:.2f}\", y={y:.2f}\", w={w:.2f}\", h={h:.2f}\"")
        print(f"  top={y:.2f}\", bottom={y+h:.2f}\"")

# Check normAutofit
print(f"\nnormAutofit present: {'<a:normAutofit' in xml}")
m = re.search(r'<a:normAutofit[^/]*/>', xml)
if m:
    print(f"  -> {m.group(0)}")

# Check line spacing
m = re.search(r'<a:spcPct val="(\d+)"', xml)
if m:
    print(f"\nLine spacing pct: {m.group(1)} (= {int(m.group(1))/1000}%)")

# Font size check
sizes = re.findall(r'sz="(\d+)"', xml)
sizes_pt = [int(s) / 100 for s in sizes]
body_sizes = [s for s in sizes_pt if s < 24]  # exclude title (24pt) and footer (smaller)
print(f"\nBody font sizes used: {sorted(set(body_sizes))}")

# Paragraph dump
print("\n=== Body text ===")
paras = re.findall(r'<a:p>(.*?)</a:p>', xml, flags=re.S)
for i, p in enumerate(paras):
    runs = re.findall(r'<a:r>(.*?)</a:r>', p, flags=re.S)
    full = ''
    for r in runs:
        t = re.search(r'<a:t[^>]*>([^<]*)</a:t>', r)
        if t:
            full += t.group(1)
    full = full.strip()
    if full and full not in ('Proposed Solution', '2', '@SIH Idea submission- Template', 'AlertX'):
        print(f"\n[P{i}] ({len(full)} chars) {full}")

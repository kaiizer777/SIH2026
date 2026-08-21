"""Verify v7 slide 4: content + geometry + font size per panel."""
import zipfile, re
from lxml import etree

SRC = r"C:\Users\bari2\Desktop\SIH2026\SIH2025-IDEA-Presentation-Format-v13.pptx"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"

z = zipfile.ZipFile(SRC)
root = etree.fromstring(z.read('ppt/slides/slide4.xml'))

print(f"{'Shape':<22} {'x':>6} {'y':>6} {'w':>6} {'h':>6}  font  autofit  content")
print("-" * 100)

for sp in root.iter(f"{{{P_NS}}}sp"):
    cNvPr = sp.find(f"{{{P_NS}}}nvSpPr/{{{P_NS}}}cNvPr")
    if cNvPr is None:
        continue
    sid = cNvPr.get("id")
    name = cNvPr.get("name", "")
    if "TextBox" not in name and "Diagonal" not in name:
        continue
    # Get geometry
    xfrm = sp.find(f".//{{{A_NS}}}xfrm")
    if xfrm is None:
        continue
    off = xfrm.find(f"{{{A_NS}}}off")
    ext = xfrm.find(f"{{{A_NS}}}ext")
    x = int(off.get("x")) / 914400 if off is not None else 0
    y = int(off.get("y")) / 914400 if off is not None else 0
    w = int(ext.get("cx")) / 914400 if ext is not None else 0
    h = int(ext.get("cy")) / 914400 if ext is not None else 0

    # Get txBody and check font size + content
    txBody = sp.find(f"{{{P_NS}}}txBody")
    if txBody is None:
        txBody = sp.find(f"{{{A_NS}}}txBody")
    if txBody is None:
        continue

    # Find any explicit font size in runs
    sizes = set()
    for r in txBody.iter(f"{{{A_NS}}}r"):
        rPr = r.find(f"{{{A_NS}}}rPr")
        if rPr is not None and rPr.get("sz"):
            sizes.add(int(rPr.get("sz")) / 100)
    font_str = ", ".join(f"{s}pt" for s in sorted(sizes)) if sizes else "default"

    # Check normAutofit
    bodyPr = txBody.find(f"{{{A_NS}}}bodyPr")
    autofit = bodyPr.find(f"{{{A_NS}}}normAutofit") if bodyPr is not None else None
    autofit_str = "yes" if autofit is not None else "no"

    # Content
    texts = txBody.xpath(".//a:t/text()", namespaces={"a": A_NS})
    first_text = texts[0][:30] if texts else ""
    para_count = len(txBody.findall(f"{{{A_NS}}}p"))

    print(f"{name[:22]:<22} {x:>6.2f} {y:>6.2f} {w:>6.2f} {h:>6.2f}  {font_str:<12} {autofit_str:<7}  {para_count}p | {first_text}...")

# Approx text height calc at 12pt × 1.2 line spacing = 14.4pt per line
print()
print("=== Approx fit check (12pt × 1.2 line spacing = 14.4pt/line) ===")
for sp in root.iter(f"{{{P_NS}}}sp"):
    cNvPr = sp.find(f"{{{P_NS}}}nvSpPr/{{{P_NS}}}cNvPr")
    if cNvPr is None:
        continue
    name = cNvPr.get("name", "")
    if "TextBox" not in name and "Diagonal" not in name:
        continue
    txBody = sp.find(f"{{{P_NS}}}txBody")
    if txBody is None:
        txBody = sp.find(f"{{{A_NS}}}txBody")
    if txBody is None:
        continue
    xfrm = sp.find(f".//{{{A_NS}}}xfrm")
    ext = xfrm.find(f"{{{A_NS}}}ext")
    h_in = int(ext.get("cy")) / 914400

    total_lines = 0
    for p in txBody.findall(f"{{{A_NS}}}p"):
        texts = p.xpath(".//a:t/text()", namespaces={"a": A_NS})
        full = ''.join(texts)
        # At 12pt ~55 chars/line for 6.5" wide
        lines = max(1, -(-len(full) // 55))
        total_lines += lines
    needed_pt = total_lines * 14.4 + (total_lines - 1) * 4  # line height + small gap
    needed_in = needed_pt / 72
    margin_in = h_in - needed_in
    status = "OK" if margin_in > 0 else "OVERFLOW"
    print(f"  {name[:30]:<30}  h={h_in:.2f}\"  need~{needed_in:.2f}\"  margin={margin_in:+.2f}\"  [{status}]")

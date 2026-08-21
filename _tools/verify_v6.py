"""Verify slide 4 of v6 — extract text from each panel."""
import zipfile, re
SRC = r"C:\Users\bari2\Desktop\SIH2026\SIH2025-IDEA-Presentation-Format-v6.pptx"
z = zipfile.ZipFile(SRC)
xml = z.read('ppt/slides/slide4.xml').decode('utf-8')

# For each shape, find the txBody and dump its <a:t> content in order
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"

from lxml import etree
root = etree.fromstring(xml.encode('utf-8'))

# Map shape id -> paragraphs
panels = {}
for sp in root.iter(f"{{{P_NS}}}sp"):
    cNvPr = sp.find(f"{{{P_NS}}}nvSpPr/{{{P_NS}}}cNvPr")
    if cNvPr is None:
        continue
    sid = cNvPr.get("id")
    name = cNvPr.get("name")
    # Find txBody - check both namespaces
    txBody = sp.find(f"{{{P_NS}}}txBody")
    if txBody is None:
        txBody = sp.find(f"{{{A_NS}}}txBody")
    if txBody is None:
        continue
    paras = []
    for p in txBody.findall(f"{{{A_NS}}}p"):
        texts = p.xpath(".//a:t/text()", namespaces={"a": A_NS})
        paras.append(''.join(texts))
    panels.setdefault(sid, []).append((name, paras))

# Print each panel
for sid in sorted(panels.keys(), key=int):
    for name, paras in panels[sid]:
        print(f"\n========= Shape id={sid}  name={name} =========")
        for i, p in enumerate(paras):
            print(f"  P{i}: {p}")

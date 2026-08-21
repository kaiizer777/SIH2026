"""Inspect both shape 25 occurrences to find the one with txBody."""
import zipfile
from lxml import etree

SRC = r"C:\Users\bari2\Desktop\SIH2026\SIH2025-IDEA-Presentation-Format-v5.pptx"
z = zipfile.ZipFile(SRC)
xml_bytes = z.read('ppt/slides/slide4.xml')

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"

tree = etree.fromstring(xml_bytes)
sps = tree.findall(f".//{{{P_NS}}}sp")
print(f"Total <p:sp> in slide4: {len(sps)}")
for i, sp in enumerate(sps):
    cNvPr = sp.find(f"{{{P_NS}}}nvSpPr/{{{P_NS}}}cNvPr")
    sid = cNvPr.get("id") if cNvPr is not None else "?"
    name = cNvPr.get("name") if cNvPr is not None else "?"
    if sid != "25":
        continue
    txBody = sp.find(f"{{{P_NS}}}txBody")
    # Also try a:txBody (it's in the a: namespace actually)
    if txBody is None:
        txBody = sp.find(f"{{{A_NS}}}txBody")
    print(f"\n--- p:sp[{i}] id={sid} name={name!r} ---")
    print(f"  has a:txBody? {txBody is not None}")
    if txBody is not None:
        n_p = len(txBody.findall(f"{{{A_NS}}}p"))
        n_texts = txBody.xpath(".//a:t/text()", namespaces={"a": A_NS})
        print(f"  paragraphs: {n_p}, text snippets: {n_texts[:3]}")
    # Parent chain
    p = sp.getparent()
    chain = []
    while p is not None:
        chain.append(etree.QName(p).localname)
        p = p.getparent()
    print(f"  ancestors: {' > '.join(chain)}")

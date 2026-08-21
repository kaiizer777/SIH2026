"""Debug: open v6 slide4.xml with lxml directly and find shape 25."""
import zipfile
from lxml import etree

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"

z = zipfile.ZipFile(r"C:\Users\bari2\Desktop\SIH2026\SIH2025-IDEA-Presentation-Format-v6.pptx")
xml_bytes = z.read('ppt/slides/slide4.xml')
root = etree.fromstring(xml_bytes)

# Count AlternateContent blocks
n_ac = len(root.findall(f".//{{{MC_NS}}}AlternateContent"))
print(f"AlternateContent blocks: {n_ac}")

# Look for shape 25 in any context
for sp in root.iter(f"{{{P_NS}}}sp"):
    cNvPr = sp.find(f"{{{P_NS}}}nvSpPr/{{{P_NS}}}cNvPr")
    if cNvPr is None or cNvPr.get("id") != "25":
        continue
    # Found
    parent = sp.getparent()
    chain = []
    while parent is not None:
        qn = etree.QName(parent)
        chain.append(f"{qn.localname}({qn.namespace[-15:]})")
        parent = parent.getparent()
    print(f"Found sp id=25. Parent chain: {' > '.join(chain)}")
    # Find txBody descendants
    txBodies = sp.findall(f".//{{{A_NS}}}txBody")
    print(f"  txBody descendants: {len(txBodies)}")
    for tb in txBodies:
        n_p = len(tb.findall(f"{{{A_NS}}}p"))
        first_text = tb.xpath(".//a:t/text()", namespaces={"a": A_NS})[:3]
        print(f"    txBody with {n_p} paragraphs, first texts: {first_text}")

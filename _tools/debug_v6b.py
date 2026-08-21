"""Debug: dump the structure of shape 25 in v6."""
import zipfile
from lxml import etree

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"

z = zipfile.ZipFile(r"C:\Users\bari2\Desktop\SIH2026\SIH2025-IDEA-Presentation-Format-v6.pptx")
root = etree.fromstring(z.read('ppt/slides/slide4.xml'))

for sp in root.iter(f"{{{P_NS}}}sp"):
    cNvPr = sp.find(f"{{{P_NS}}}nvSpPr/{{{P_NS}}}cNvPr")
    if cNvPr is None or cNvPr.get("id") != "25":
        continue
    # Print all direct children
    print(f"sp id=25 direct children:")
    for child in sp:
        qn = etree.QName(child)
        print(f"  {qn.localname} (ns: {qn.namespace[-15:]})")
        if qn.localname == "txBody":
            print(f"    Found txBody as direct child!")
        # Check for txBody descendants
        for sub in child.iter(f"{{{A_NS}}}txBody"):
            print(f"    nested txBody found inside {qn.localname}")

"""Try different find methods to locate txBody in shape 25."""
import zipfile
from lxml import etree

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"

z = zipfile.ZipFile(r"C:\Users\bari2\Desktop\SIH2026\SIH2025-IDEA-Presentation-Format-v6.pptx")
root = etree.fromstring(z.read('ppt/slides/slide4.xml'))

# Find sp id=25 in Choice
for sp in root.iter(f"{{{P_NS}}}sp"):
    cNvPr = sp.find(f"{{{P_NS}}}nvSpPr/{{{P_NS}}}cNvPr")
    if cNvPr is None or cNvPr.get("id") != "25":
        continue
    # Walk up to check Choice
    parent = sp.getparent()
    in_choice = False
    while parent is not None:
        qn = etree.QName(parent)
        if qn.namespace == MC_NS and qn.localname == "Choice":
            in_choice = True
            break
        elif qn.namespace == MC_NS and qn.localname == "Fallback":
            break
        parent = parent.getparent()
    if not in_choice:
        continue

    print(f"Found sp id=25 in Choice")

    # Try multiple find methods
    print(f"  Method 1 (find direct): {sp.find(f'{{{A_NS}}}txBody') is not None}")
    print(f"  Method 2 (findall direct): {len(sp.findall(f'{{{A_NS}}}txBody'))} found")
    print(f"  Method 3 (findall .//): {len(sp.findall(f'.//{{{A_NS}}}txBody'))} found")
    print(f"  Method 4 (iter all): {sum(1 for _ in sp.iter(f'{{{A_NS}}}txBody'))} found")
    print(f"  Method 5 (findall {A}txBody no quotes): {len(sp.findall(f'{A}txBody'))} found")
    print(f"  Method 6 (findall any txBody): {len(sp.findall(f'.//txBody'))} found")
    print(f"  Method 7 (xpath): {len(sp.xpath('.//a:txBody', namespaces={'a': A_NS}))} found")

    # What about iter() of the sp?
    all_tags = []
    for el in sp.iter():
        all_tags.append(etree.QName(el).localname)
    print(f"  All tags under sp: {all_tags[:20]}")
    break

"""Verify v5 - find TextBox 12 by shape id=13 specifically."""
import zipfile, re
SRC = r"C:\Users\bari2\Desktop\SIH2026\SIH2025-IDEA-Presentation-Format-v5.pptx"
z = zipfile.ZipFile(SRC)
xml = z.read('ppt/slides/slide2.xml').decode('utf-8')

# Find the <p:sp> whose name is "TextBox 12"
m = re.search(r'<p:sp>\s*<p:nvSpPr>\s*<p:cNvPr id="(\d+)" name="TextBox 12"', xml)
if m:
    sid = m.group(1)
    print(f"Found TextBox 12 with shape id={sid}")
    # Find the full sp block starting from this match
    start = m.start()
    end = xml.index('</p:sp>', start) + len('</p:sp>')
    sp_xml = xml[start:end]
    # Geometry
    off = re.search(r'<a:off x="(\d+)" y="(\d+)"/>', sp_xml)
    ext = re.search(r'<a:ext cx="(\d+)" cy="(\d+)"/>', sp_xml)
    if off and ext:
        x = int(off.group(1)) / 914400
        y = int(off.group(2)) / 914400
        w = int(ext.group(1)) / 914400
        h = int(ext.group(2)) / 914400
        print(f"  Geometry: x={x:.3f}\", y={y:.3f}\", w={w:.3f}\", h={h:.3f}\"")
        print(f"  Top={y:.2f}\"  Bottom={y+h:.2f}\"")
        print(f"  Vertical room: {h:.2f}\"")
    # normAutofit inside this sp
    autofit = re.search(r'<a:normAutofit[^/]*/?>', sp_xml)
    if autofit:
        print(f"  Autofit: {autofit.group(0)}")
else:
    print("TextBox 12 not found")

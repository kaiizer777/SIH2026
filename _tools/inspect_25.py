"""Inspect raw XML around shape id 25."""
import zipfile, re
SRC = r"C:\Users\bari2\Desktop\SIH2026\SIH2025-IDEA-Presentation-Format-v5.pptx"
z = zipfile.ZipFile(SRC)
xml = z.read('ppt/slides/slide4.xml').decode('utf-8')

# Find each cNvPr with id="25" and show 300 chars of context
for m in re.finditer(r'<p:cNvPr id="25"[^>]*>', xml):
    start = max(0, m.start() - 100)
    end = min(len(xml), m.end() + 600)
    print("---")
    print(xml[start:end])
    print("---")

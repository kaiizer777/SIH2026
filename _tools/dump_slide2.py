import zipfile, re
z = zipfile.ZipFile(r'C:\Users\bari2\Desktop\SIH2026\SIH2025-IDEA-Presentation-Format-rewritten.pptx')
xml = z.read('ppt/slides/slide2.xml').decode('utf-8')
# Find all <a:t>...</a:t> text nodes
for m in re.findall(r'<a:t[^>]*>([^<]*)</a:t>', xml):
    if m.strip():
        print(repr(m))

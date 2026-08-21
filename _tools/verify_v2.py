import zipfile, re
SRC = r"C:\Users\bari2\Desktop\SIH2026\SIH2025-IDEA-Presentation-Format-v2.pptx"
z = zipfile.ZipFile(SRC)
xml = z.read('ppt/slides/slide2.xml').decode('utf-8')

print("=== Text + bold map ===")
runs = re.findall(r'<a:r>(.*?)</a:r>', xml, flags=re.S)
for r in runs:
    b = 'b="1"' in r
    t = re.search(r'<a:t[^>]*>([^<]*)</a:t>', r)
    if t:
        text = t.group(1)
        if text.strip():
            tag = 'BOLD' if b else '    '
            print(f"[{tag}] {text}")

print("\n=== Title preserved ===")
print("Title 'Proposed Solution' present:", 'Proposed Solution' in xml)

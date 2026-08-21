import zipfile, re
SRC = r"C:\Users\bari2\Desktop\SIH2026\SIH2025-IDEA-Presentation-Format-v3.pptx"
z = zipfile.ZipFile(SRC)
xml = z.read('ppt/slides/slide2.xml').decode('utf-8')

# Title check
print("Title 'Proposed Solution' preserved:", '>Proposed Solution<' in xml or 'Proposed Solution' in xml)

# Paragraph count via <a:p> ... </a:p>
paras = re.findall(r'<a:p>(.*?)</a:p>', xml, flags=re.S)
print(f"Paragraph count: {len(paras)}")

# For each paragraph, gather runs (bold/text)
print("\n=== Slide 2 body ===")
for i, p in enumerate(paras):
    runs = re.findall(r'<a:r>(.*?)</a:r>', p, flags=re.S)
    parts = []
    for r in runs:
        b = 'b="1"' in r
        t = re.search(r'<a:t[^>]*>([^<]*)</a:t>', r)
        if t:
            tag = '**' if b else ''
            parts.append(f"{tag}{t.group(1)}{tag}")
    text = ''.join(parts)
    if text.strip():
        print(f"\n[P{i}] {text}")

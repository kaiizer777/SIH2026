"""Find the actual ID of the Supporting Facts shape in slide 4."""
import zipfile, re
SRC = r"C:\Users\bari2\Desktop\SIH2026\SIH2025-IDEA-Presentation-Format-v5.pptx"
z = zipfile.ZipFile(SRC)
xml = z.read('ppt/slides/slide4.xml').decode('utf-8')

# Find all p:sp and p:sp shape IDs
for m in re.finditer(r'<p:(?:sp|cxnSp|pic|graphicFrame)>.*?</p:(?:sp|cxnSp|pic|graphicFrame)>', xml, flags=re.S):
    block = m.group(0)
    id_m = re.search(r'<p:cNvPr id="(\d+)" name="([^"]+)"', block)
    if id_m:
        sid, name = id_m.group(1), id_m.group(2)
        # Snippet of text
        txt_m = re.findall(r'<a:t[^>]*>([^<]+)</a:t>', block)
        snippet = ' | '.join(txt_m)[:120]
        print(f"id={sid:>5}  name={name!r}  text={snippet!r}")

"""Compare slide4.xml between v5 (input) and v6 (python-pptx saved)."""
import zipfile
for label, path in [
    ("v5 (input)", r"C:\Users\bari2\Desktop\SIH2026\SIH2025-IDEA-Presentation-Format-v5.pptx"),
    ("v6 (output)", r"C:\Users\bari2\Desktop\SIH2026\SIH2025-IDEA-Presentation-Format-v6.pptx"),
]:
    z = zipfile.ZipFile(path)
    xml = z.read('ppt/slides/slide4.xml').decode('utf-8')
    print(f"\n=== {label} ===")
    print(f"  Length: {len(xml)} bytes")
    print(f"  Has mc:AlternateContent: {'<mc:AlternateContent' in xml}")
    print(f"  Has 'Supporting Facts': {'Supporting Facts' in xml}")
    print(f"  Has 'Diagonal Corners Snipped': {'Diagonal Corners Snipped' in xml}")
    # Count sps
    n_sp = xml.count('<p:sp>')
    print(f"  Number of <p:sp>: {n_sp}")

import PyPDF2

try:
    reader = PyPDF2.PdfReader('20180545574_001_00003_00010589.pdf')
    for i, page in enumerate(reader.pages):
        print(f"--- PAGE {i+1} ---")
        print(page.extract_text())
except Exception as e:
    print(f"Error: {e}")

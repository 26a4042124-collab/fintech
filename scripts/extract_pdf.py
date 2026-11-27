
import pymupdf
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r'c:\Users\nguye\Documents\BAITAP\DAIHOC\3 CNDVTC\fintech\FinLab.pdf'
out_dir = r'c:\Users\nguye\Documents\BAITAP\DAIHOC\3 CNDVTC\fintech\static\pdf_preview'
os.makedirs(out_dir, exist_ok=True)

doc = pymupdf.open(pdf_path)
print(f'Total pages: {len(doc)}')

for i in range(len(doc)):
    page = doc[i]
    text = page.get_text()
    print(f'=== Page {i+1} TEXT ===')
    print(text[:600])

    mat = pymupdf.Matrix(2, 2)
    pix = page.get_pixmap(matrix=mat)
    img_path = os.path.join(out_dir, f'page_{i+1:02d}.png')
    pix.save(img_path)
    print(f'  -> saved: {img_path}')
    print()

print('Done!')

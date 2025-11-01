import sys
import re
try:
    from pypdf import PdfReader
except Exception:
    try:
        from PyPDF2 import PdfReader
    except Exception:
        print('No PDF reader library found (pypdf or PyPDF2).')
        raise

paths = [
    'data/2025+노인보건복지사업안내(1권).pdf',
    'data/2025+노인보건복지사업안내(2권).pdf',
]

# Keywords likely to appear in section headings
keywords = [
    '노인', '요양', '일자리', '경로당', '장기요양', '경로효친', '복지', '수당', '지원금',
    '건강보험', '방문요양', '신청', '절차', '프로그램', '문화', '여가', '학대', '쉼터', '급여',
    '운영', '기준', '사업안내', '사업', '지원사업'
]

numbered_re = re.compile(r'^\s*\d{1,2}(?:[-\.\d]*)?\s+.+')

def looks_like_heading(line):
    if not line:
        return False
    s = line.strip()
    if len(s) < 3 or len(s) > 140:
        return False
    # numbered headings like '1 노인복지 일반현황' or '4-1 어버이날 행사'
    if numbered_re.match(s):
        return True
    # lines with common keywords
    for k in keywords:
        if k in s:
            # avoid very long sentences
            return True
    return False

for p in paths:
    print('='*80)
    print('FILE:', p)
    try:
        reader = PdfReader(p)
    except Exception as e:
        print('ERROR opening', p, e)
        continue

    headings = {}
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ''
        except Exception:
            text = ''
        for line in text.splitlines():
            line = line.strip()
            if looks_like_heading(line):
                # normalize spaces
                key = re.sub(r'\s+', ' ', line)
                if key not in headings:
                    headings[key] = []
                headings[key].append(i+1)

    if not headings:
        print('No candidate headings found (maybe text extraction failed).')
    else:
        print('\nFound candidate headings (line -> pages):\n')
        # sort by appearance (min page)
        items = sorted(headings.items(), key=lambda kv: min(kv[1]))
        for h, pages in items:
            print(f"- {h}  (pages: {', '.join(map(str, pages[:5]))}{'...' if len(pages)>5 else ''})")

print('\nDone')

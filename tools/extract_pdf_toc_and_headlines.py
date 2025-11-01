import sys
try:
    # prefer pypdf if available
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

for p in paths:
    print('='*80)
    print('FILE:', p)
    try:
        reader = PdfReader(p)
    except Exception as e:
        print('ERROR opening', p, e)
        continue
    # outlines (bookmarks)
    try:
        outlines = reader.outline
    except Exception:
        outlines = None
    if outlines:
        print('\nOutlines / Bookmarks:')
        def dump_outlines(outlines, depth=0):
            for o in outlines:
                if isinstance(o, list):
                    dump_outlines(o, depth+1)
                else:
                    title = getattr(o, 'title', str(o))
                    print('  '*depth + '- ' + str(title))
        dump_outlines(outlines)
    else:
        print('\nNo outlines/bookmarks found')

    # print first 5 pages' first lines
    print('\nSample text from first 8 pages:')
    for i, page in enumerate(reader.pages[:8]):
        text = page.extract_text()
        print(f'-- Page {i+1} --')
        if text:
            for line in text.splitlines()[:5]:
                print('   ', line.strip())
        else:
            print('   (no text)')
    print('\n')

print('Done')

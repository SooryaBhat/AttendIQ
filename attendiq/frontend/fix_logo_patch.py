from pathlib import Path
import os
import re

base = Path('attendiq/frontend')
logo = Path('attendiq/frontend/assets/images/logo.svg')
if not logo.exists():
    raise FileNotFoundError(f'logo.svg not found at {logo}')

html_files = list(base.rglob('*.html'))
print(f'Found {len(html_files)} HTML files')
icon_pattern = re.compile(r'<link\s+rel=["\']icon["\']', re.I)
brand_pattern = re.compile(r'<(div|span)\s+class=["\']brand-mark["\']>\s*AIQ\s*</\1>', re.I)

for path in html_files:
    text = path.read_text(encoding='utf-8')
    rel = Path(os.path.relpath(logo, path.parent)).as_posix()
    changed = False

    if not icon_pattern.search(text):
        insert = (
            f'    <link rel="icon" type="image/svg+xml" href="{rel}" />\n'
            f'    <link rel="shortcut icon" href="{rel}" />\n'
        )
        if '</title>' in text:
            text = text.replace('</title>', f'</title>\n{insert}', 1)
        elif '<head>' in text:
            text = text.replace('<head>', '<head>\n' + insert, 1)
        elif '</head>' in text:
            text = text.replace('</head>', insert + '</head>', 1)
        changed = True

    def repl(m):
        tag = m.group(1)
        return (
            f'<{tag} class="brand-mark">'
            f'<img src="{rel}" alt="AttendIQ logo" '
            f'onerror="this.style.display=\'none\'; this.nextElementSibling.style.display=\'inline-block\';" />'
            f'<span class="brand-text-fallback" style="display:none;">AIQ</span>'
            f'</{tag}>'
        )

    text, num = brand_pattern.subn(repl, text)
    if num > 0:
        changed = True

    if changed:
        path.write_text(text, encoding='utf-8')
        print('Updated', path)

#!/usr/bin/env python3
"""Exporter les rapports techniques en PDF."""

import html
from pathlib import Path
import re

import markdown
from weasyprint import HTML

ROOT = Path(__file__).resolve().parents[1]
STYLE = '''
@page { size: A4; margin: 19mm 18mm 20mm; @bottom-left { content: "AD10 · GuillaumeYves"; font-size: 9pt; color: #64748b; } @bottom-right { content: counter(page); font-size: 9pt; } }
body { font-family: DejaVu Sans, sans-serif; font-size: 10pt; line-height: 1.5; color: #172033; }
h1 { font-size: 22pt; color: #173c66; line-height: 1.2; margin-top: 0; }
h2 { font-size: 14pt; color: #173c66; margin-top: 7mm; }
h1, h2, h3 { break-after: avoid; }
p, li { orphans: 3; widows: 3; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #f1f5f9; padding: 3mm; font-size: 8pt; }
code { font-family: DejaVu Sans Mono, monospace; font-size: 8pt; overflow-wrap: anywhere; }
table { width: 100%; border-collapse: collapse; margin: 4mm 0; font-size: 9pt; }
th, td { border: 1px solid #cbd5e1; text-align: left; padding: 2mm; }
th { background: #e8eef6; }
tr { break-inside: avoid; }
img { max-width: 100%; max-height: 220mm; object-fit: contain; }
a { color: #185a91; text-decoration: none; }
.chapter { break-before: page; }
'''


def render(path):
    content = markdown.markdown(path.read_text(), extensions=['tables', 'fenced_code'])

    def local_image(match):
        source = match.group(1)
        return 'src="' + html.escape((path.parent / source).resolve().as_uri(), quote=True) + '"'

    content = re.sub(r'src="(?!https?://)([^"]+)"', local_image, content)

    def repository_link(match):
        target = match.group(1)
        relative = (path.parent / target).resolve().relative_to(ROOT)
        return 'href="https://github.com/GuillaumeYves/tp-ad10/blob/main/' + html.escape(relative.as_posix(), quote=True) + '"'

    return re.sub(r'href="(?!https?://|#)([^"]+)"', repository_link, content)


def main():
    chapters = []
    for name in ['tp1', 'tp2', 'tp3', 'tp4', 'tp5', 'final']:
        content = render(ROOT / name / 'README.md')
        document = '<!doctype html><meta charset="utf-8"><meta name="author" content="GuillaumeYves"><title>Rapport AD10 : ' + name + '</title><style>' + STYLE + '</style>' + content
        HTML(string=document, base_url=str(ROOT)).write_pdf(ROOT / name / 'report.pdf')
        chapters.append('<article class="chapter">' + content + '</article>')
    cover = '<h1>Administration avancée de serveurs Linux</h1><p>Travaux pratiques et projet intégrateur</p><p>GuillaumeYves<br>28 octobre 2026</p><p>Rapports techniques, configurations et résultats observés sur les VM du laboratoire.</p>'
    document = '<!doctype html><meta charset="utf-8"><meta name="author" content="GuillaumeYves"><title>Rapport complet AD10</title><style>' + STYLE + '</style>' + cover + ''.join(chapters)
    HTML(string=document, base_url=str(ROOT)).write_pdf(ROOT / 'docs/rapport-complet.pdf')
    print('Six rapports et docs/rapport-complet.pdf créés.')


if __name__ == '__main__':
    main()

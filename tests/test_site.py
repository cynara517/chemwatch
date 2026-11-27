"""Checks for published navigation, assets and the reviewed bilingual copy."""
import json
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'
class Page(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.shared=[];self.in_shared=False
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='header' and attrs.get('class')=='site-header':self.in_shared=True
        if self.in_shared and tag=='a':self.shared.append(attrs.get('href',''))
        self.links.extend(attrs[k] for k in ('src','href') if k in attrs)
    def handle_endtag(self,tag):
        if tag=='header':self.in_shared=False
class SiteTests(unittest.TestCase):
    def test_published_links_and_assets_exist(self):
        for path in DIST.rglob('*.html'):
            page=Page();page.feed(path.read_text())
            for link in page.links:
                u=urlsplit(link)
                if u.scheme or u.netloc or not u.path:continue
                self.assertTrue((path.parent/unquote(u.path)).exists(),f'{path}: {link}')
    def test_three_sections_remain_reachable_from_each_page(self):
        for path in DIST.rglob('*.html'):
            page=Page();page.feed(path.read_text())
            targets={(path.parent/urlsplit(link).path).resolve() for link in page.shared}
            for dest in ['index.html','benchmarks/index.html','papers/index.html','chemwatch.html']:
                self.assertIn((DIST/dest).resolve(),targets,str(path))
    def test_public_copy_and_image_provenance(self):
        copy=json.loads((ROOT/'content/papers-translations.json').read_text())
        self.assertGreater(len(copy),300)
        self.assertTrue(all(isinstance(x,str) and x.strip() for x in copy.values()))
        papers=(DIST/'papers/app.js').read_text()
        self.assertNotIn('审核草稿',papers)
        self.assertNotIn('待补充',papers.replace('研究时期待补充',''))
        attribution=(DIST/'papers/assets/ATTRIBUTION.md').read_text()
        self.assertIn('CC BY-NC 4.0',attribution)
        self.assertFalse((DIST/'papers/interview.md').exists())

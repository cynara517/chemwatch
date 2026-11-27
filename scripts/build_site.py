"""Assemble CynaraWatch's shared navigation and reviewed bilingual paper copy."""
from pathlib import Path
import json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'
def header(section,base=''):
 links=[('benchmarks','benchmarks/index.html','My Benchmarks'),('papers','papers/index.html','My Papers'),('chemwatch','chemwatch.html','ChemWatch')]
 nav=''.join(f'<a href="{base}{url}"'+(' aria-current="page"' if key==section else '')+f'>{label}</a>' for key,url,label in links)
 return f'<header class="site-header"><a class="brand" href="{base}index.html"><span class="site-mark" aria-hidden="true">C·</span> CynaraWatch</a><nav aria-label="主导航" data-en-aria="Main navigation">{nav}</nav><div class="language-switch" role="group" aria-label="语言" data-en-aria="Language"><button type="button" data-lang="zh" lang="zh-CN" aria-pressed="true">中文</button><button type="button" data-lang="en" lang="en" aria-pressed="false">EN</button></div></header>'
def chrome(path,section,base='',subnav=''):
 s=path.read_text()
 s=re.sub(r'<header\b.*?</header>',header(section,base),s,count=1,flags=re.S)
 s=re.sub(r'<nav class="section-nav".*?</nav>','',s,flags=re.S)
 if subnav:s=s.replace('</header>','</header>'+subnav,1)
 if 'site-nav.css' not in s:s=s.replace('</head>',f'<link rel="stylesheet" href="{base}site-nav.css"></head>')
 if 'site-nav.js' not in s:s=s.replace('</body>',f'<script src="{base}site-nav.js"></script></body>')
 path.write_text(s)
subprocess.run([sys.executable,str(ROOT/'scripts/build_benchmarks.py')],check=True)
for path in (DIST/'benchmarks').glob('*.html'):
 s=path.read_text().replace(' · ChemWatch',' · CynaraWatch').replace('ChemWatch / Shifan Chen','CynaraWatch / Shifan Chen')
 path.write_text(s);chrome(path,'benchmarks','../')
chemnav='<nav class="section-nav" aria-label="ChemWatch"><a href="#overview" data-nav="overview" data-en="Overview">概览</a><a href="#catalog" data-nav="catalog" data-en="Catalog">数据目录</a><a href="#connect" data-nav="connect" data-en="Connect an agent">连接 Agent</a><a href="#method" data-nav="method" data-en="Methods">统计方法</a></nav>'
chrome(DIST/'chemwatch.html','chemwatch',subnav=chemnav)
papernav='<nav class="section-nav" aria-label="论文导航" data-en-aria="Paper navigation"><a href="#overview" data-en="Research overview">研究概览</a><a href="#publications" data-en="All publications">全部成果</a><a href="#undergraduate" data-en="Undergraduate explorations">本科探索</a><a href="#about" data-en="About & collaboration">关于与合作</a></nav>'
chrome(DIST/'papers/index.html','papers','../',papernav)
(DIST/'index.html').write_text((ROOT/'content/home.html').read_text().replace('<!-- SITE_HEADER -->',header('home')))
translations=json.loads((ROOT/'content/papers-translations.json').read_text())
(DIST/'papers/translations.js').write_text('window.paperEnglish = '+json.dumps(translations,ensure_ascii=False,indent=2)+';\n')
print('Built CynaraWatch navigation, home and bilingual papers.')

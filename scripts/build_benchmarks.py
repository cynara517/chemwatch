"""Build Shifan Chen's bilingual, static benchmark design notes from curated content."""
from pathlib import Path
from html import escape
import json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'dist/benchmarks'
DATA=json.loads((ROOT/'content/benchmarks.json').read_text())
SCORES=json.loads((OUT/'archive/2026-11-27-model-scores.json').read_text())
TASKS=DATA['tasks']

def pair(zh,en):return {'zh':zh,'en':en}
def text(value):return escape(value)
def bi(tag,zh,en=None,attrs=''):
 if isinstance(zh,dict):zh,en=zh['zh'],zh['en']
 return f'<{tag}{(" "+attrs) if attrs else ""} data-en="{escape(en,quote=True)}">{escape(zh)}</{tag}>'
def p(zh,en=None,attrs=''):return bi('p',zh,en,attrs)
def a(url,zh,en,attrs=''):return bi('a',zh,en,attrs=f'href="{escape(url,quote=True)}" {attrs}')
def ext(url,zh,en):return a(url,zh,en,'target="_blank" rel="noopener noreferrer"')

def shell(title,body,detail=False):
 return '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'''+bi('title',title['zh']+' · ChemWatch',title['en']+' · ChemWatch')+'''<meta name="description" content="Shifan Chen 的科学 Agent 评测设计笔记：灵感、科研意义、工具、科学验收与模型表现。" data-en-content="Shifan Chen's scientific-agent benchmark notes: inspiration, scientific motivation, tools, verification and model performance."><link rel="stylesheet" href="portfolio.css"></head><body>'''+a('#main','跳到正文','Skip to content','class="skip"')+'''<header><a class="brand" href="../index.html"><span class="brandmark">C·</span> ChemWatch</a><nav aria-label="专题导航" data-en-aria="Portfolio navigation">'''+a('../index.html','数据观测站','Observatory')+a('index.html','我的 Benchmark 设计','My benchmark designs', '' if detail else 'aria-current="page"')+'''<a href="https://github.com/cynara517/chemwatch">GitHub</a></nav><div class="language-switch" role="group" aria-label="语言" data-en-aria="Language"><button type="button" data-lang="zh" lang="zh-CN" aria-pressed="true">中文</button><button type="button" data-lang="en" lang="en" aria-pressed="false">EN</button></div></header><main id="main">'''+body+'''</main><footer>'''+bi('span','ChemWatch / Shifan Chen · 科学 Agent 评测设计笔记','ChemWatch / Shifan Chen · Scientific-agent benchmark design notes')+bi('span','题目条目与成绩摘录自 DeltaScience；设计笔记由 Shifan Chen 撰写。','Task entries and scores are excerpted from DeltaScience; design notes are by Shifan Chen.')+bi('span','个人贡献展示 · 非 DeltaScience 或 Terminal-Bench-Science 官方网站','Personal contribution portfolio · Not an official DeltaScience or Terminal-Bench-Science website')+a('archive/2026-11-27-model-scores.json','原站成绩快照','Source score snapshot')+'''</footer><script src="../i18n.js"></script><script src="portfolio.js"></script></body></html>'''

def papers(keys):
 out='<div class="papers">'
 for key in keys:
  r=DATA['references'][key]
  out+=f'<a class="paper" href="{r["url"]}" target="_blank" rel="noopener noreferrer">'+bi('span','论文 / 项目原始来源','Original paper / project',attrs='class="paper-label"')+bi('strong',r['title'])+bi('span',r['meta'])+bi('span','访问原始主页','Visit original page',attrs='class="paper-action"')+'</a>'
 return out+'</div>'

def scoretable(task):
 rows=[]
 for m in sorted(SCORES['models'],key=lambda m:-(m['scores'][task] if m['scores'][task] is not None else -1)):
  score=m['scores'][task];n=sum(r[0] is not None for r in m['rounds'][task])
  value='—' if score is None else f'{score:.2f}'
  partial=bi('small',f'已出分 {n}/5 轮',f'{n}/5 rounds scored') if n<5 else ''
  rows.append(f'<tr><th scope="row">{text(m["model"])}</th><td>{text(m["harness"])}</td><td class="score"><strong>{value}</strong>{partial}</td></tr>')
 return bi('h3','原站模型表现','Model performance on DeltaScience')+p('摘录自 DeltaScience · 原站快照 2026-11-25 · 保存于 2026-11-27。','Excerpted from DeltaScience · Source snapshot: 2026-11-25 · Saved: 2026-11-27.',attrs='class="source-note"')+'<div class="score-scroll"><table class="score-table"><thead><tr>'+bi('th','LLM 名称','LLM',attrs='scope="col"')+bi('th','Harness 架构','Harness',attrs='scope="col"')+bi('th','分数 / 100','Score / 100',attrs='scope="col"')+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'+p('分数沿用原站已出分轮次的均分，保留两位小数；未出分轮次不计入，已确认的失败与超时计 0 分。部分轮次结果已单独标明。','Scores follow the source mean over scored rounds, rounded to two decimals. Pending rounds are excluded; confirmed failures and timeouts count as zero. Incomplete sets of rounds are marked.',attrs='class="source-note"')+'<div class="score-sources">'+ext(SCORES['source'],'查看 DeltaScience','View DeltaScience')+a('archive/2026-11-27-model-scores.json','下载成绩快照','Download score snapshot','download')+'</div>'

cards=''
for t in TASKS:
 cards+=f'<a class="task-card" href="{t["id"].lower()}.html"><div class="task-top"><span class="code">{t["id"]}</span>'+bi('span',t['field'])+'</div>'+bi('h3',t['title'])+p(t['question'])+bi('span','阅读设计笔记','Read the design notes',attrs='class="read"')+'</a>'
body='<section class="hero"><p class="eyebrow">RESEARCH NOTES / BENCHMARK DESIGN</p>'+bi('h1','从科研灵感，到可验收的 Agent 任务。','From scientific inspiration to verifiable agent tasks.')+p('我为 DeltaScience 贡献了 C-01、CSF-1、CSF-2、CSF-3 四道化学题。这里记录它们从研究阅读到任务设计的过程，以及我从模型运行与验收记录中得到的反思。','I contributed four chemistry tasks to DeltaScience: C-01, CSF-1, CSF-2 and CSF-3. These notes trace their development from research reading to task design, alongside reflections on model execution and verification.',attrs='class="lead"')+'<div class="hero-links">'+a('#tasks','探索四道题','Explore the four tasks','class="button"')+a('#standards','与 Terminal-Bench-Science 的联系','Connection to Terminal-Bench-Science','class="text-link"')+'</div><div class="byline">'+bi('span','作者署名：Shifan Chen','By Shifan Chen')+a('https://deltascience.bohrium.com/','摘录自原网站 DeltaScience','Excerpted from the original DeltaScience website')+'</div></section>'
body+='<section class="design-path" aria-label="设计方法" data-en-aria="Design approach">'
for z,e,z2,e2 in [('灵感来源','Inspiration','论文与研究展示','Papers and research demonstrations'),('科学问题','Scientific question','明确研究边界','Define the scientific scope'),('任务实现','Implementation','工具与交付物','Tools and deliverables'),('评价与反思','Evaluation and reflection','独立验收证据','Independent verification')]:
 body+='<div>'+bi('span',z,e)+bi('strong',z2,e2)+'</div>'
body+='</section><section id="tasks"><div class="section-title"><p class="eyebrow">MY CONTRIBUTIONS</p>'+bi('h2','四道题，四种科学执行能力','Four tasks, four facets of scientific execution')+p('很高兴参与设计，四个题从化学角度出发，我想考察 LLM 在有机合成、计算化学方面的表现。','I am glad to have contributed to the design. These four tasks take a chemistry perspective to examine how LLMs perform in organic synthesis and computational chemistry.')+'</div><div class="task-grid">'+cards+'</div></section>'
body+='<section id="standards" class="standards"><div><p class="eyebrow">METHOD / TERMINAL-BENCH-SCIENCE</p>'+bi('h2','以 TBS 的任务标准，审视自己的设计。','Examining my designs through the TBS task standards.')+p('我的题目设计与审查以 Terminal-Bench-Science 的公开标准为参照，关注真实科研工作流、可复现环境、独立验收，以及题面与测试的一致性。','My task design and review take the public Terminal-Bench-Science standards as a reference, focusing on real research workflows, reproducible environments, independent verification and alignment between instructions and tests.')+ext('https://github.com/harbor-framework/terminal-bench-science/blob/f3566474429773b0b22735ff636457f57c7935c9/rubrics/task-implementation.toml','查看所参照版本的官方 rubric','Read the referenced official rubric')+'</div><dl class="principles">'
for z,e,zd,ed in [('科学问题可执行','Executable scientific questions','把文献问题落实为明确输入、工具、交付物与研究边界。','Translate research questions into explicit inputs, tools, deliverables and scientific boundaries.'),('关键结果可核验','Verifiable results','用独立计算检查科学产物，而非依赖模型的完成声明。','Check scientific outputs with independent computation rather than relying on a model’s completion claim.'),('结果解释有边界','Bounded interpretations','区分科学失败、格式问题、基础设施异常及尚未评分。','Distinguish scientific failure, format errors, infrastructure problems and unscored runs.'),('用轨迹改进任务','Learning from trajectories','发现协议歧义和实现差异时，先检视验收契约，再解释模型表现。','When protocol ambiguity or implementation differences arise, examine the verification contract before interpreting model performance.')]:body+='<div>'+bi('dt',z,e)+bi('dd',zd,ed)+'</div>'
body+='</dl></section><section class="takeaways"><p class="eyebrow">WHAT I LEARNED</p>'+bi('h2','分数之外，我更关注证据如何形成。','Beyond scores, I care about how evidence is built.')+'<div class="lesson-grid">'
for z,e,zd,ed in [('工具调用之后','After the tool call','能运行软件只是开始。关键结果是否可重算、数值关系是否一致，决定产物能否支撑科学判断。','Running software is a beginning. Reproducible results and consistent numerical relationships determine whether outputs can support scientific judgments.'),('零分之内','Inside a zero score','提交缺失、环境失败、科学指标未达标和定义歧义，需要分别分析，才知道下一步应改模型还是改任务。','Missing submissions, environment failures, unmet scientific criteria and ambiguous definitions need separate diagnosis to identify what should improve.'),('设计者的责任','The designer’s responsibility','明确标准、校准容差、保留版本差异，与设置有挑战性的科学目标同样重要。','Clear criteria, calibrated tolerances and version-aware interpretation matter as much as challenging scientific objectives.')]:body+='<article>'+bi('h3',z,e)+p(zd,ed)+'</article>'
body+='</div></section><section id="outlook" class="outlook"><p class="eyebrow">A PERSONAL PERSPECTIVE</p>'+bi('h2','拥抱 AI for Science，从理解开始。','Embrace AI for Science, beginning with understanding.')+p('与其在焦虑中等待 AI 改变科学，不如主动拥抱 AI for Science：从第一性原理出发，理解它的能力与边界，在真实科研问题中学会使用它，以可验证的证据推动发现。','Rather than waiting anxiously for AI to reshape science, I choose to embrace AI for Science: reason from first principles, understand its capabilities and limits, learn to use it on real research problems, and ground discovery in verifiable evidence.',attrs='class="personal-statement"')+'<span class="statement-author">Shifan Chen</span><div class="quotes">'
quotes=[
 ('鄂维南','Weinan E','年轻人要抓住机遇，突破既有学科框架和思维惯性。','Young people should seize the opportunity and break beyond existing disciplinary frameworks and habitual ways of thinking.','《光明日报》访谈《AI时代 我们需要什么样的科研人才》· 2026-11-23 · 原文节选','Guangming Daily interview: What kind of research talent do we need in the AI era? · 2026-11-23 · Translated excerpt','https://m.gmw.cn/2026-11/23/content_39115699.htm'),
 ('埃隆·马斯克','Elon Musk','你必须从第一性原理出发，从根基上构建推理。','you have to build up the reasoning from the ground up from first principles','The Henry Ford 口述访谈 · 2008 · 节选中译','The Henry Ford oral history · 2008 · Excerpt','https://www.thehenryford.org/docs/thehenryfordlibraries/innovator-transcripts/transcript_musk_full-length.pdf#page=20'),
 ('吴恩达','Andrew Ng','AI 不会取代工作者，但使用 AI 的工作者会取代不使用 AI 的工作者。','AI won’t replace workers, but workers who use AI will replace workers who don’t.','The Batch 专栏中引用的观点 · 中译','A common refrain cited in The Batch · Original wording','https://www.deeplearning.ai/the-batch/how-ai-is-affecting-the-job-market-and-what-you-can-do-about-it')]
for name,ename,q,eq,label,elabel,url in quotes:
 body+='<figure class="quote">'+bi('blockquote',q,eq)+'<figcaption>'+bi('strong',name,ename)+ext(url,label,elabel)+'</figcaption></figure>'
body+='</div></section>'
(OUT/'index.html').write_text(shell(pair('我的 Benchmark 设计','My benchmark designs'),body))
for i,t in enumerate(TASKS):
 b='<div class="breadcrumb">'+a('index.html#tasks','全部设计笔记','All design notes')+f'<span>/ {t["id"]}</span></div><section class="detail-hero"><div class="eyebrow">{t["id"]} / '+bi('span',t['field'])+'</div>'+bi('h1',t['title'])+p(t['question'],attrs='class="lead"')+'<p class="version">v1.0</p></section><div class="task-layout"><aside class="contents">'+bi('span','本篇内容','On this page')
 for anchor,z,e in [('origin','灵感与设计','Inspiration and design'),('meaning','科研意义','Scientific motivation'),('tools','科学工具','Scientific tools'),('criteria','科学验收','Verification criteria'),('observations','模型表现与反思','Performance and reflections'),('papers','论文与来源','Papers and sources')]:b+=a('#'+anchor,z,e)
 b+='</aside><div class="article-body"><section id="origin"><p class="eyebrow">FROM READING TO DESIGN</p>'+bi('h2','灵感如何成为一道题','Turning inspiration into a task')+p(t['origin'])+p(t['design'])+'</section><section id="meaning">'+bi('h2','科研意义','Scientific motivation')+p(t['meaning'])+'</section><section id="tools">'+bi('h2','科学工具','Scientific tools')+'<ul class="tool-list">'
 for name,desc in t['tools']:b+='<li>'+bi('strong',name)+bi('span',desc)+'</li>'
 b+='</ul></section><section id="criteria">'+bi('h2','科学验收标准','Scientific verification criteria')+p('这里展示验收维度与科学含义。','The criteria below describe the dimensions of verification and their scientific purpose.',attrs='class="intro-note"')+'<dl class="criteria">'
 for name,desc in t['criteria']:b+='<div>'+bi('dt',name)+bi('dd',desc)+'</div>'
 b+='</dl></section><section id="observations">'+bi('h2','模型表现与设计反思','Model performance and design reflections')+scoretable(t['id'])+'<div class="reflection">'+bi('span','我的设计反思','My design reflections',attrs='class="label"')+p(t['reflection'])+'</div></section><aside class="boundary">'+bi('h3','科学解释的边界','Scope of scientific interpretation')+p(t['limit'])+'</aside><section id="papers">'+bi('h2','论文与灵感来源','Papers and inspiration')+p('原始研究属于各论文和项目作者；本页呈现我如何将阅读转化为任务设计。','The original research belongs to its paper and project authors. These notes describe how I translated reading into task design.',attrs='class="intro-note"')+papers(t['refs'])+'</section></div></div><nav class="next-notes" aria-label="其他设计笔记" data-en-aria="More design notes">'+a('index.html#tasks','返回四道题','Back to the four tasks')+a(TASKS[(i+1)%4]['id'].lower()+'.html','下一篇：'+TASKS[(i+1)%4]['title']['zh'],'Next: '+TASKS[(i+1)%4]['title']['en'])+'</nav>'
 (OUT/(t['id'].lower()+'.html')).write_text(shell(pair(t['id']+' · '+t['title']['zh'],t['id']+' · '+t['title']['en']),b,True))
print('Built five bilingual pages with 44 model/harness score rows.')

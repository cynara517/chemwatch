"use strict";
const TOPICS = [
 {id:"retrosynthesis",name:"逆合成",en:"Retrosynthesis",icon:"⇌",desc:"从单步反应到多步路线",featured:true},
 {id:"coupling",name:"偶联与杂环",en:"Coupling & heterocycles",icon:"C—C",desc:"C–C / C–N / C–H 与更多成键"},
 {id:"materials",name:"材料化学",en:"Materials",icon:"◇",desc:"材料性质、晶体稳定性与发现"},
 {id:"yield",name:"产率预测",en:"Reaction yield",icon:"η",desc:"实验产率与反应条件优化"},
 {id:"free-energy",name:"自由能预测",en:"Free energy",icon:"ΔG",desc:"反应、水合、结合与势垒"},
 {id:"selectivity",name:"ee 与选择性",en:"Stereoselectivity",icon:"R / S",desc:"不对称催化与 ΔΔG‡"},
 {id:"bioactivity",name:"药物活性",en:"Bioactivity",icon:"⊕",desc:"活性、亲和力与评估套件"},
 {id:"bioprocess",name:"工业生物过程",en:"Industrial bioprocess",icon:"⌁",desc:"青霉素 · 红霉素 · 发酵过程"}
];
const EXTRA = [{id:"penicillin",name:"青霉素生产"},{id:"erythromycin",name:"红霉素生产"}];
const LABELS = Object.fromEntries([...TOPICS,...EXTRA].map(x=>[x.id,x.name]));
const KINDS = {dataset:"DATASET",benchmark:"BENCHMARK",database:"DATABASE",resource:"RESOURCE"};
let catalog, observations, history;
let activeTopic="", codeMode="install", toastTimer;
const $ = s=>document.querySelector(s);
const $$ = s=>[...document.querySelectorAll(s)];
const escapeHTML = s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const countFamilies = entries=>new Set(entries.filter(e=>e.kind==="dataset").map(e=>e.family_id)).size;
const countKind = (entries,kind)=>entries.filter(e=>e.kind===kind).length;
const topicEntries = id=>catalog.entries.filter(e=>e.topics.includes(id));
function showToast(text){$("#toast").textContent=text;$("#toast").classList.add("show");clearTimeout(toastTimer);toastTimer=setTimeout(()=>$("#toast").classList.remove("show"),3000);}
function download(data,name){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:"application/json"}));const a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}
function renderOverview(){
 $("#topic-grid").innerHTML=TOPICS.map(t=>{const es=topicEntries(t.id);return `<button class="topic-tile ${t.featured?"featured":""}" data-topic="${t.id}"><span class="tile-arrow">↗</span><span class="topic-icon">${t.icon}</span><h3>${t.name}</h3><p>${t.desc}</p><div class="tile-foot"><span>${countFamilies(es)} 数据集家族</span><span>${countKind(es,"benchmark")} benchmark</span></div></button>`;}).join("");
 $$(".topic-tile").forEach(el=>el.addEventListener("click",()=>{activeTopic=el.dataset.topic;location.hash="catalog";renderCatalog();}));
 renderCoverage();
 const success=observations?.items?.length||0;
 const failures=observations?.errors?.length||0;
 $("#signals").innerHTML=`<div class="signal"><strong>目录核验</strong><p>${catalog.reviewed_at} · ${catalog.entries.length} 个已收录条目</p></div><div class="signal"><strong>上游版本观测</strong><p>${escapeHTML(observations?.checked_at?.slice(0,10)||"尚无记录")} · ${success} 个已保存基线，最近检查失败 ${failures} 项。</p></div><div class="signal"><strong>候选来源</strong><p><a href="#method">查看论文、GitHub 与 Hugging Face 检索结果 ↗</a></p></div>`;
 $("#review-date").textContent="目录核验 · "+catalog.reviewed_at;
 const events=observations?.events||[];
 if(events.length){
  $(".status-badge").textContent="来源变化";
  $("#signals").innerHTML=events.slice(0,3).map(event=>`<div class="signal"><span class="date">${escapeHTML((event.observed_at||observations.checked_at).slice(0,10))} / UPSTREAM SIGNAL</span><strong>${escapeHTML(event.name)}</strong><p>${escapeHTML(event.observation.note)} · <a href="${escapeHTML(event.observation.url)}" target="_blank" rel="noopener">查看证据 ↗</a></p></div>`).join("");
 }
}
function renderCoverage(){
 const kind=$("#coverage-mode").value;const values=TOPICS.map(t=>({name:t.name,value:kind==="dataset"?countFamilies(topicEntries(t.id)):countKind(topicEntries(t.id),"benchmark")}));const max=Math.max(1,...values.map(v=>v.value));$("#coverage").innerHTML=values.map(v=>`<div class="bar-row"><span>${v.name}</span><div class="bar-track"><div class="bar-fill" style="width:${100*v.value/max}%"></div></div><span class="bar-count">${v.value}</span></div>`).join("");
 const points=history?.points||[];
 if(points.length<2){$("#history-chart").innerHTML="";return;}
 const metric=kind==="dataset"?"dataset_families":"benchmark_suites";
 const maximum=Math.max(1,...points.map(p=>p[metric]));
 const start=new Date(points[0].date).valueOf(),span=Math.max(1,new Date(points.at(-1).date).valueOf()-start);
 const coords=points.map(p=>[15+450*(new Date(p.date).valueOf()-start)/span,85-65*p[metric]/maximum]);
 const line=coords.map((p,i)=>i===0?`M${p[0]},${p[1]}`:`H${p[0]}V${p[1]}`).join(" ");
 $("#history-chart").innerHTML=`<div class="panel-foot">真实收录历史 · ${kind==="dataset"?"数据集家族":"Benchmark套件"}</div><svg viewBox="0 0 480 115" role="img" aria-label="从${points[0].date}到${points.at(-1).date}的目录覆盖历史"><path d="M15 85H465" stroke="#dce3dd" fill="none"/><path d="${line}" stroke="#176d59" stroke-width="2" fill="none"/>${coords.map((p,i)=>`<circle cx="${p[0]}" cy="${p[1]}" r="3" fill="#176d59"><title>${points[i].date}: ${points[i][metric]}</title></circle>`).join("")}<text x="15" y="108" fill="#6a7775" font-size="9">${points[0].date}</text><text x="465" y="108" text-anchor="end" fill="#6a7775" font-size="9">${points.at(-1).date}</text></svg>`;
 $("#history-note").textContent="历史按实际观测日积累；同一天保留最后快照。目录增长不等于全领域数据增长。";
}
function matchesTarget(entry,target){if(!target)return true;const text=[...entry.targets,entry.description].join(" | ");if(target==="ΔG")return /(^|[^Δ])ΔG(?!‡)/.test(text);if(target==="ΔG‡")return /(^|[^Δ])ΔG‡/.test(text);return text.includes(target);}
function getResults(){const search=$("#search").value.trim().toLowerCase(),kind=$("#kind").value,origin=$("#origin").value,target=$("#target").value;return catalog.entries.filter(e=>(!activeTopic||e.topics.includes(activeTopic))&&(!kind||kind===e.kind)&&(!origin||e.data_origin.includes(origin))&&matchesTarget(e,target)&&(!search||[e.name,e.description,e.notes,e.data_origin,...e.targets,...e.topics].join(" ").toLowerCase().includes(search)));}
function renderCatalog(){
 $("#topic-tabs").innerHTML=[{id:"",name:"全部"},...TOPICS,...EXTRA].map(t=>`<button data-topic="${t.id}" class="${activeTopic===t.id?"active":""}" aria-pressed="${activeTopic===t.id}">${t.name}<span>${t.id?topicEntries(t.id).length:catalog.entries.length}</span></button>`).join("");
 $$("#topic-tabs button").forEach(b=>b.addEventListener("click",()=>{activeTopic=b.dataset.topic;renderCatalog();}));
 const entries=getResults();
 $("#results-summary").innerHTML=`<span><strong>${entries.length}</strong> 个目录条目 · ${countFamilies(entries)} 个数据集家族 · ${countKind(entries,"benchmark")} 个benchmark套件</span><span>全部保留原始来源 · 非全领域普查</span>`;
 let context="";
 if(activeTopic==="retrosynthesis")context="逆合成专项：USPTO 各版本属于同一家族。按家族追溯最早已核实的公开版，可在首页单独查看逆合成数据集与评估套件的时间线。";
 if(activeTopic==="coupling")context="偶联按广义范围持续收录：已覆盖C–C、C–N、C–H直接芳基化与杂环相关实验；C–O、C–S、C–B等专用集待核验补充。";
 if(["bioprocess","penicillin","erythromycin"].includes(activeTopic))context="优先化工生产：IndPenSim是工业规模机理模拟，EFP来自真实工厂。滴度/得率/生产强度、分离纯化等字段需要逐项核验；现有记录不代表这些目标均已具备。";
 if(activeTopic==="free-energy")context="保留物理量定义：反应ΔG、水合ΔG、结合ΔG、势垒ΔG‡分别标注；选择性ΔΔG‡请见ee与选择性专题。";
 $("#topic-context").innerHTML=context?`<div class="context-note">${context}</div>`:"";
 $("#cards").innerHTML=entries.length?entries.map(e=>{
 const obs=observations?.items?.find(o=>o.id===e.id);
 return `<article class="data-card"><div class="card-top"><span class="kind ${e.kind}">${KINDS[e.kind]}</span><span class="year">${e.publication_year} / 来源年份</span></div><h3>${escapeHTML(e.name)}</h3><p class="description">${escapeHTML(e.description)}</p><div class="tags">${e.targets.map(t=>`<span class="tag">${escapeHTML(t)}</span>`).join("")}</div><div class="card-meta"><div><div class="meta-label">${e.record_count!==null?"来源版本规模":"记录规模"}</div><div class="meta-count">${e.record_count!==null?e.record_count.toLocaleString()+`<small>${escapeHTML(e.record_unit)}</small>`:'<small>待核实 · 不估算</small>'}</div></div><div><div class="meta-label">数据来源</div><div>${escapeHTML(e.data_origin)}</div></div></div><details><summary>证据与统计口径</summary><p>${escapeHTML(e.notes)}</p><p><a href="${escapeHTML(e.date_source||e.url)}" target="_blank" rel="noopener">查看年代依据 ↗</a></p>${e.count_note?`<p>计数依据：${escapeHTML(e.count_note)}</p>`:""}<p>数据许可：${escapeHTML(e.data_license)}。核验日期：${e.verified_at}。家族：${escapeHTML(e.family_id)}。</p>${e.doi?`<p>DOI：${escapeHTML(e.doi)}</p>`:""}${e.monitor?`<p>监测：${e.monitor.type==="github"?escapeHTML(e.monitor.repo)+(e.monitor.path?" / "+escapeHTML(e.monitor.path):"")+" 的提交变化，须再核实数据内容":e.monitor.type==="huggingface"?"Hugging Face 数据集修订":"Zenodo存档版本与文件校验和"}。</p>`:'<p>暂未配置自动来源探测。</p>'}${obs?`<p>最近观测：<a href="${escapeHTML(obs.url)}" target="_blank" rel="noopener">${escapeHTML(obs.revision.slice(0,12))}</a>；${escapeHTML(obs.note)}</p>`:""}</details><div class="card-footer"><a href="${escapeHTML(e.url)}" target="_blank" rel="noopener">打开原始来源 ↗</a><span class="monitor">${obs?"● 已建立版本基线":e.monitor?"○ 可检查上游":"人工核验"}</span></div></article>`;
 }).join(""):'<div class="empty"><b>这个交叉方向尚未收录。</b>调整筛选即可查看其他资源。没有结果表示目录覆盖缺口。</div>';
}
function route(){const id=location.hash.slice(1).split("?")[0]||"overview";const valid=["overview","catalog","connect","method"].includes(id)?id:"overview";$$(".view").forEach(el=>el.hidden=el.id!==valid);$$("[data-nav]").forEach(el=>el.classList.toggle("active",el.dataset.nav===valid));if(valid==="catalog"&&catalog)renderCatalog();window.scrollTo({top:0,behavior:"instant"});}
function shellQuote(s){return "'"+s.replace(/'/g,"'\\''")+"'";}
function config(){return {agent:$("#agent-type").value,skillDirectory:$("#skill-directory").value.trim(),topics:$$("#subscribe-topics input:checked").map(el=>el.value),mode:$("#source-mode").value,source:$("#remote-source").value.trim(),delivery:$("#delivery").value,email:$("#email").value.trim()};}
function renderCommand(){
 const c=config(),remote=c.mode==="remote";
 $("#skill-directory").hidden=c.agent!=="custom";$("#remote-source").hidden=!remote;$("#email").hidden=c.delivery!=="email";
 $("#source-note").textContent=remote?"默认使用GitHub公开JSON，无需账号。也可以指定自己维护的公开目录。":"本地文件只反映当前快照；上游版本探测仍可用。";
 const source=remote?(c.source||"https://cynara517.github.io/chemwatch/data/catalog.json"):"./dist/data/catalog.json";
 const flags=c.topics.map(t=>" --topic "+t).join("");
 const mail=c.delivery==="email"?" --email "+shellQuote(c.email||"you@example.com"):"";
 const cmd="~/.local/bin/chemwatch follow --source "+shellQuote(source)+flags+mail;
 const install="curl -fsSL https://cynara517.github.io/chemwatch/install.sh | sh -s -- "+(c.agent==="custom"?"--skill-dir "+shellQuote(c.skillDirectory||"./.agents/skills"):"--agent codex");
 const selected=c.topics.length?c.topics.map(t=>LABELS[t]).join("、"):"全部方向";
 let text;
 if(codeMode==="install")text=install+"\n\n# 然后在你的 AI 中说：\n# 使用 $chemwatch-monitor 每天监测："+selected+"。\n# 有变化或检查失败时报告，无变化保持安静。\n\n# 安装只添加 CLI + skill；持续监测由 harness 调度\n# 或 chemwatch watch --background 执行。";
 else if(codeMode==="cli")text="# 安装后保存订阅，首次建立基线\n\n"+cmd+"\n\n# 每天在本机检查（电脑需开机）\n~/.local/bin/chemwatch watch --background --interval 86400\n\n# 随时检查 / 查看状态 / 停止\n~/.local/bin/chemwatch check --json\n~/.local/bin/chemwatch watch --status\n~/.local/bin/chemwatch watch --stop";
 else if(codeMode==="schedule")text="# harness 原生调度可执行：\n~/.local/bin/chemwatch check --json\n\n# 无调度器时可用本地 watcher：\n~/.local/bin/chemwatch watch --background --interval 86400\n\n# 云端个人订阅：\ntemplates/subscribe.yml\n# 设置主题与可选SMTP Secrets，再启用schedule。\n\n# 公开站点自身每日更新，个人监测由订阅者运行。";
 else text="请从 https://github.com/cynara517/chemwatch 安装并使用 chemwatch-monitor Agent Skill。\n\n一行安装命令：\n"+install+"\n\n关注："+selected+"。保存订阅：\n"+cmd+"\n\n请先阅读 SKILL.md。若当前不是Codex，使用本harness真正支持的skills根目录，不假定DeepSeek有固定安装路径。\n首次只建立基线。之后每天检查；优先使用本harness实际可用的调度器，没有调度能力时运行CLI的watch --background，并告诉我实际启动了哪种机制。\n无变化保持安静；目录新增、元数据变化或上游版本信号出现时，读取报告并附原始来源。仓库提交变化须核实后才能认定为数据发布。\n"+(c.delivery==="email"?"邮件发给 "+(c.email||"待填写的地址")+"；从运行环境读取SMTP配置，未配置就明确报告。":"通过当前harness支持的通知方式报告；如不支持则保存在本地报告中并明确说明。");
 $("#command").textContent=text;
 $("#command-hint").textContent=codeMode==="install"?"标准 Agent Skill · 无需平台账号 · 不修改模型设置":"CLI + SKILL.md · 使用公开GitHub数据源";
 $$("[data-code]").forEach(b=>b.classList.toggle("active",b.dataset.code===codeMode));
}
function setupConnect(){let saved;try{saved=JSON.parse(localStorage.getItem("chemwatch-subscription")||"null");}catch{}$("#subscribe-topics").innerHTML=[...TOPICS,...EXTRA].map(t=>`<label><input type="checkbox" value="${t.id}" ${(saved?.topics||["retrosynthesis"]).includes(t.id)?"checked":""}>${t.name}</label>`).join("");$("#remote-source").value="https://cynara517.github.io/chemwatch/data/catalog.json";if(saved){$("#agent-type").value=saved.agent||"codex";$("#skill-directory").value=saved.skillDirectory||"./.agents/skills";$("#source-mode").value=saved.mode||"remote";$("#remote-source").value=saved.source||"https://cynara517.github.io/chemwatch/data/catalog.json";$("#delivery").value=saved.delivery||"report";$("#email").value=saved.email||"";}$$("#subscribe-topics input, #source-mode, #remote-source, #delivery, #email, #agent-type, #skill-directory").forEach(el=>el.addEventListener("input",renderCommand));$$("[data-code]").forEach(b=>b.addEventListener("click",()=>{codeMode=b.dataset.code;renderCommand();}));renderCommand();}
async function init(){try{
 const r=await fetch("data/catalog.json",{cache:"no-cache"});if(!r.ok)throw Error("目录HTTP "+r.status);catalog=await r.json();if(catalog.schema_version!=="1.0")throw Error("目录版本不兼容");
 const optional=await Promise.allSettled([fetch("data/observations.json",{cache:"no-cache"}).then(r=>r.ok?r.json():null),fetch("data/history.json",{cache:"no-cache"}).then(r=>r.ok?r.json():null)]);observations=optional[0].status==="fulfilled"?optional[0].value:null;history=optional[1].status==="fulfilled"?optional[1].value:null;
 renderOverview();setupConnect();route();loadTimeline();loadInbox();
 $("#coverage-mode").addEventListener("change",renderCoverage);["#search","#kind","#origin","#target"].forEach(id=>$(id).addEventListener("input",renderCatalog));
 $("#reset").addEventListener("click",()=>{activeTopic="";["#search","#kind","#origin","#target"].forEach(id=>$(id).value="");renderCatalog();});
 $("#export").addEventListener("click",()=>download({...catalog,entries:getResults(),export_filter:{topic:activeTopic,search:$("#search").value,kind:$("#kind").value,origin:$("#origin").value,target:$("#target").value}},"chemwatch-selection.json"));
 $("#save-subscription").addEventListener("click",()=>{const c=config();if(c.mode==="remote"){try{const url=new URL(c.source);if(!["http:","https:"].includes(url.protocol))throw Error();}catch{showToast("请填写有效的公开 HTTP(S) JSON 地址");return;}}if(c.delivery==="email"&&!$("#email").checkValidity()||c.delivery==="email"&&!c.email){showToast("请填写接收报告的邮箱");return;}try{localStorage.setItem("chemwatch-subscription",JSON.stringify(c));showToast("已保存到此浏览器；复制指令交给AI可启用监测");}catch{showToast("浏览器未允许保存；仍可复制指令使用");}});
 $("#copy-command").addEventListener("click",async()=>{try{await navigator.clipboard.writeText($("#command").textContent);showToast("已复制，可交给你的 Agent 执行");}catch{const range=document.createRange();range.selectNodeContents($("#command"));getSelection().removeAllRanges();getSelection().addRange(range);showToast("浏览器未允许自动复制，已选中指令，请手动复制");}});
}catch(e){$("#error").hidden=false;$("#error").textContent="目录暂时无法读取："+e.message+"。请通过HTTP服务器打开，或稍后刷新。";}}
window.addEventListener("hashchange",route);init();

"use strict";
const TOPICS = [
  {id:"retrosynthesis",name:"逆合成",en:"Retrosynthesis",desc:["单步反应与多步路线","Single-step reactions and multistep routes"]},
  {id:"coupling",name:"偶联与杂环",en:"Coupling & heterocycles",desc:["C–C、C–N、C–H 与其他成键","C–C, C–N, C–H and other bond formations"]},
  {id:"materials",name:"材料化学",en:"Materials chemistry",desc:["材料性质与晶体稳定性","Material properties and crystal stability"]},
  {id:"yield",name:"产率预测",en:"Reaction yield",desc:["实验产率与条件优化","Experimental yields and condition optimization"]},
  {id:"free-energy",name:"自由能预测",en:"Free energy",desc:["反应、水合、结合与势垒","Reaction, hydration, binding and activation"]},
  {id:"selectivity",name:"ee 与选择性",en:"Stereoselectivity",desc:["不对称催化与 ΔΔG‡","Asymmetric catalysis and ΔΔG‡"]},
  {id:"bioactivity",name:"药物活性",en:"Bioactivity",desc:["活性与结合亲和力","Activity and binding affinity"]},
  {id:"bioprocess",name:"工业生物过程",en:"Industrial bioprocesses",desc:["青霉素与红霉素生产","Penicillin and erythromycin production"]}
];
const EXTRA = [{id:"penicillin",name:"青霉素生产",en:"Penicillin production"},{id:"erythromycin",name:"红霉素生产",en:"Erythromycin production"}];
const topicsById=Object.fromEntries([...TOPICS,...EXTRA].map(t=>[t.id,t]));
const topicName=id=>id?tr(topicsById[id].name,topicsById[id].en):tr("全部方向","All topics");
const kindName=kind=>({dataset:tr("数据集","Dataset"),benchmark:"Benchmark",database:tr("数据库","Database"),resource:tr("资源","Resource")})[kind];
const $=s=>document.querySelector(s);
const $$=s=>Array.from(document.querySelectorAll(s));
const escapeHTML=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const countFamilies=entries=>new Set(entries.filter(e=>e.kind==="dataset").map(e=>e.family_id)).size;
const countKind=(entries,kind)=>entries.filter(e=>e.kind===kind).length;
const topicEntries=id=>catalog.entries.filter(e=>e.topics.includes(id));
const number=n=>n.toLocaleString(locale());
const quantity=(n,zh,one,many)=>number(n)+" "+tr(zh,n===1?one:many);
const publicSource="https://cynara517.github.io/chemwatch/data/catalog.json";
let catalog, observations, snapshots, translations={}, activeTopic="", codeMode="install", toastTimer;
function localizedEntry(e){return language==="en"&&translations[e.id]?{...e,...translations[e.id]}:e;}
function sourceName(name){
  const e=catalog?.entries.find(row=>row.name===name);
  return e?localizedEntry(e).name:name;
}
function showToast(text){
  $("#toast").textContent=text;$("#toast").classList.add("show");clearTimeout(toastTimer);
  toastTimer=setTimeout(()=>$("#toast").classList.remove("show"),3000);
}
function download(data,name){
  const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:"application/json"}));
  const a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);
}
function signalNote(obs){
  const en={repository_change:"The repository or data path has a new commit.",dataset_repository_revision:"The dataset repository revision changed.",archive_version_or_files:"The archive version or file checksum changed."};
  return tr(obs.note,en[obs.signal]||"The upstream source revision changed.");
}
function renderOverview(){
  $("#topic-grid").innerHTML=TOPICS.map(t=>{
    const entries=topicEntries(t.id);
    return `<button class="topic-tile" data-topic="${t.id}"><span class="tile-arrow">↗</span><h3>${topicName(t.id)}</h3><p>${tr(...t.desc)}</p><div class="tile-foot">${quantity(countFamilies(entries),"个家族","family","families")} · ${quantity(countKind(entries,"benchmark"),"个套件","suite","suites")}</div></button>`;
  }).join("");
  $$(".topic-tile").forEach(el=>el.onclick=()=>{activeTopic=el.dataset.topic;location.hash="catalog";renderCatalog();});
  renderCoverage();
  const checked=observations?.checked_at?.slice(0,10)||"—", events=observations?.events||[];
  $(".status-badge").textContent=events.length?tr("来源变化","Updates"):tr("基线","Baseline");
  $("#review-date").textContent=tr("目录核验","Catalog reviewed")+" · "+catalog.reviewed_at;
  $("#signals").innerHTML=events.length?events.slice(0,3).map(e=>`<div class="signal"><small>${escapeHTML((e.observed_at||checked).slice(0,10))}</small><strong>${escapeHTML(sourceName(e.name))}</strong><p>${escapeHTML(signalNote(e.observation))} <a href="${escapeHTML(e.observation.url)}">${tr("证据","Source")} ↗</a></p></div>`).join(""):
    `<div class="signal"><strong>${tr("目录核验","Catalog review")}</strong><p>${catalog.reviewed_at} · ${quantity(catalog.entries.length,"个已核验条目","reviewed entry","reviewed entries")}</p></div><div class="signal"><strong>${tr("上游版本","Upstream revisions")}</strong><p>${checked} · ${quantity(observations?.items?.length||0,"个基线","baseline","baselines")} · ${quantity(observations?.errors?.length||0,"项检查失败","failed check","failed checks")}</p></div><a href="#method">${tr("查看来源检索结果","Browse source searches")} ↗</a>`;
}
function renderCoverage(){
  const kind=$("#coverage-mode").value;
  const values=TOPICS.map(t=>({name:topicName(t.id),value:kind==="dataset"?countFamilies(topicEntries(t.id)):countKind(topicEntries(t.id),"benchmark")}));
  const max=Math.max(1,...values.map(v=>v.value));
  $("#coverage").innerHTML=values.map(v=>`<div class="bar-row"><span>${v.name}</span><div class="bar-track"><div class="bar-fill" style="width:${100*v.value/max}%"></div></div><span>${v.value}</span></div>`).join("");
  const points=snapshots?.points||[];
  if(points.length<2){$("#history-chart").replaceChildren();return;}
  const metric=kind==="dataset"?"dataset_families":"benchmark_suites", maximum=Math.max(1,...points.map(p=>p[metric]));
  const start=Date.parse(points[0].date),span=Math.max(1,Date.parse(points.at(-1).date)-start);
  const coords=points.map(p=>[15+450*(Date.parse(p.date)-start)/span,69-54*p[metric]/maximum]);
  const line=coords.map(([x,y],i)=>i?`H${x}V${y}`:`M${x} ${y}`).join(" ");
  $("#history-chart").innerHTML=`<svg viewBox="0 0 480 94" role="img" aria-label="${tr("目录覆盖历史","Catalog coverage over time")}"><path d="${line}" fill="none" stroke="var(--aqua)" stroke-width="2"/>${coords.map(([x,y],i)=>`<circle cx="${x}" cy="${y}" r="3" fill="var(--aqua)"><title>${points[i].date} · ${points[i][metric]}</title></circle>`).join("")}<g fill="var(--muted)" font-size="11"><text x="15" y="90">${points[0].date}</text><text x="465" y="90" text-anchor="end">${points.at(-1).date}</text></g></svg>`;
}
function matchesTarget(e,target){
  if(!target)return true;
  const s=[...e.targets,e.description].join(" | ");
  if(target==="ΔG")return /(^|[^Δ])ΔG(?!‡)/.test(s);
  if(target==="ΔG‡")return /(^|[^Δ])ΔG‡/.test(s);
  return s.includes(target);
}
function getResults(){
  const search=$("#search").value.trim().toLowerCase(),kind=$("#kind").value,origin=$("#origin").value,target=$("#target").value;
  return catalog.entries.filter(e=>{
    if((activeTopic&&!e.topics.includes(activeTopic))||(kind&&kind!==e.kind)||(origin&&!e.data_origin.includes(origin))||!matchesTarget(e,target))return false;
    if(!search)return true;
    const copy=translations[e.id]||{};
    return [e.name,e.description,e.notes,e.data_origin,...e.targets,...e.topics,copy.name,copy.description,copy.notes,copy.data_origin,...(copy.targets||[])].join(" ").toLowerCase().includes(search);
  });
}
const contextCopy={
  retrosynthesis:["USPTO 各版本合并为一个家族，最早可核实的公开版决定时间线起点。","USPTO editions share one family. Its timeline starts at the earliest verified public edition."],
  coupling:["目前已收录 C–C、C–N、C–H 直接芳基化与杂环相关实验。C–O、C–S、C–B 专用集仍待核验。","Coverage includes C–C, C–N, direct C–H arylation and heterocycle experiments. Dedicated C–O, C–S and C–B sets await review."],
  bioprocess:["IndPenSim 是工业规模机理模拟，EFP 来自真实工厂。滴度、得率、生产强度与分离纯化等字段按来源核实。","IndPenSim simulates industrial-scale production. EFP contains factory measurements. Titer, yield, productivity and downstream variables require source-level verification."],
  "free-energy":["反应、水合、结合 ΔG 与势垒 ΔG‡ 分列。选择性 ΔΔG‡ 见 ee 与选择性专题。","Reaction, hydration and binding ΔG are distinguished from activation ΔG‡. Selectivity ΔΔG‡ is indexed under stereoselectivity."]
};
function entryCard(raw){
  const e=localizedEntry(raw),obs=observations?.items?.find(o=>o.id===e.id);
  const link=(url,label)=>`<a href="${escapeHTML(url)}" target="_blank" rel="noopener">${escapeHTML(label)} ↗</a>`;
  const monitor=e.monitor,probe=monitor?.type==="github"?monitor.repo+(monitor.path?" / "+monitor.path:""):
    monitor?.type==="huggingface"?tr("Hugging Face 数据集修订","Hugging Face dataset revision"):tr("Zenodo 版本与文件校验和","Zenodo version and file checksum");
  return `<article class="data-card" data-entry="${escapeHTML(e.id)}"><div class="card-top"><span class="kind ${e.kind}">${kindName(e.kind)}</span><span class="year">${e.publication_year}</span></div>
    <h3>${escapeHTML(e.name)}</h3><p class="description">${escapeHTML(e.description)}</p>
    <div class="tags">${e.targets.map(t=>`<span class="tag">${escapeHTML(t)}</span>`).join("")}</div>
    <div class="card-meta"><div><div class="meta-label">${tr("来源版本规模","Edition size")}</div><div class="meta-count">${e.record_count!=null?number(e.record_count)+" <small>"+escapeHTML(e.record_unit)+"</small>":tr("待核实","Unverified")}</div></div>
    <div><div class="meta-label">${tr("数据来源","Origin")}</div>${escapeHTML(e.data_origin)}</div></div>
    <details><summary>${tr("证据与统计口径","Evidence and counting rules")}</summary>
    ${e.notes?"<p>"+escapeHTML(e.notes)+"</p>":""}<p>${link(e.date_source||e.url,tr("年代依据","Date evidence"))}</p>
    ${e.count_note?"<p>"+escapeHTML(e.count_note)+"</p>":""}<p>${tr("数据许可","Data license")} · ${escapeHTML(e.data_license)}<br>${tr("核验日期","Reviewed")} · ${escapeHTML(e.verified_at)}<br>${tr("家族","Family")} · ${escapeHTML(e.family_id)}</p>
    ${e.doi?"<p>DOI · "+escapeHTML(e.doi)+"</p>":""}<p>${monitor?tr("监测","Monitor")+" · "+escapeHTML(probe):tr("人工核验来源","Manually reviewed source")}</p>
    ${obs?"<p>"+link(obs.url,obs.revision.slice(0,12))+" · "+escapeHTML(signalNote(obs))+"</p>":""}</details>
    <div class="card-footer">${link(e.url,tr("原始来源","Original source"))}<small>${obs?tr("已建立基线","Baseline recorded"):monitor?tr("可监测","Monitored source"):tr("人工核验","Reviewed")}</small></div></article>`;
}
function renderCatalog(){
  const openIds=new Set($$("#cards details[open]").map(el=>el.closest("article").dataset.entry));
  $("#topic-tabs").innerHTML=[{id:""},...TOPICS,...EXTRA].map(t=>`<button data-topic="${t.id}" aria-pressed="${activeTopic===t.id}">${topicName(t.id)} <span>${t.id?topicEntries(t.id).length:catalog.entries.length}</span></button>`).join("");
  $$("#topic-tabs button").forEach(b=>b.onclick=()=>{activeTopic=b.dataset.topic;renderCatalog();});
  const entries=getResults();
  $("#results-summary").textContent=`${quantity(entries.length,"个条目","entry","entries")} · ${quantity(countFamilies(entries),"个数据集家族","dataset family","dataset families")} · ${quantity(countKind(entries,"benchmark"),"个评估套件","benchmark suite","benchmark suites")}`;
  const context=contextCopy[["penicillin","erythromycin"].includes(activeTopic)?"bioprocess":activeTopic];
  $("#topic-context").innerHTML=context?`<p class="context-note">${tr(...context)}</p>`:"";
  $("#cards").innerHTML=entries.length?entries.map(entryCard).join(""):`<div class="empty">${tr("没有符合条件的已收录条目。可调整关键词或筛选条件。","No catalog entries match. Try another search term or filter.")}</div>`;
  $$("#cards article").filter(a=>openIds.has(a.dataset.entry)).forEach(a=>a.querySelector("details").open=true);
}
function route(){
  const id=location.hash.slice(1).split("?")[0], valid=["overview","catalog","connect","method"].includes(id)?id:"overview";
  $$(".view").forEach(el=>el.hidden=el.id!==valid);
  $$("[data-nav]").forEach(el=>{el.classList.toggle("active",el.dataset.nav===valid);if(el.dataset.nav===valid)el.setAttribute("aria-current","page");else el.removeAttribute("aria-current");});
  if(valid==="catalog"&&catalog)renderCatalog();
  window.scrollTo({top:0,behavior:"instant"});
}
function shellQuote(s){return "'"+s.replace(/'/g,"'\\''")+"'";}
function config(){return {agent:$("#agent-type").value,skillDirectory:$("#skill-directory").value.trim(),topics:$$("#subscribe-topics input:checked").map(el=>el.value),mode:$("#source-mode").value,source:$("#remote-source").value.trim(),delivery:$("#delivery").value,email:$("#email").value.trim()};}
function renderCommand(){
  const c=config();
  $("#skill-directory").hidden=c.agent!=="custom";$("#remote-source").hidden=c.mode!=="remote";$("#email").hidden=c.delivery!=="email";
  $("#agent-note").textContent=c.agent==="codex"?tr("用户级技能目录 · ~/.agents/skills","User skill directory · ~/.agents/skills"):tr("填写当前 harness 实际加载的技能目录。","Enter the skills directory your harness loads.");
  $("#source-note").textContent=c.mode==="remote"?tr("读取公开 JSON，也支持你自己的目录地址。","Reads a public JSON catalog. You can supply your own URL."):tr("读取本地快照，仍可探测上游版本。","Reads a local snapshot and can still probe upstream revisions.");
  $("#command").textContent=agentCommand(c,codeMode,c.topics.map(topicName),language);
  $("#command-hint").textContent=codeMode==="install"?tr("Agent Skill · macOS / Linux · Python 3.10+","Agent Skill · macOS / Linux · Python 3.10+"):tr("公开目录 · CLI 与 Agent Skill","Public catalog · CLI and Agent Skill");
  $$("[data-code]").forEach(b=>{b.classList.toggle("active",b.dataset.code===codeMode);b.setAttribute("aria-pressed",String(b.dataset.code===codeMode));});
}
function setupConnect(){
  let saved;
  try{saved=JSON.parse(localStorage.getItem("chemwatch-subscription")||"null");}catch{}
  $("#subscribe-topics").innerHTML=[...TOPICS,...EXTRA].map(t=>`<label><input type="checkbox" value="${t.id}" ${(saved?.topics||["retrosynthesis"]).includes(t.id)?"checked":""}><span>${topicName(t.id)}</span></label>`).join("");
  $("#remote-source").value=saved?.source||publicSource;
  if(saved){
    $("#agent-type").value=saved.agent||"codex";$("#skill-directory").value=saved.skillDirectory||"./.agents/skills";
    $("#source-mode").value=saved.mode||"remote";$("#delivery").value=saved.delivery||"report";$("#email").value=saved.email||"";
  }
  $$("#subscribe-topics input,#source-mode,#remote-source,#delivery,#email,#agent-type,#skill-directory").forEach(el=>el.oninput=renderCommand);
  $$("[data-code]").forEach(b=>b.onclick=()=>{codeMode=b.dataset.code;renderCommand();});
  renderCommand();
}
function saveSubscription(){
  const c=config();
  if(c.mode==="remote"){
    try{if(!["http:","https:"].includes(new URL(c.source).protocol))throw Error();}
    catch{showToast(tr("请输入公开的 HTTP(S) JSON 地址。","Enter a public HTTP(S) catalog URL."));return;}
  }
  if(c.delivery==="email"&&(!c.email||!$("#email").checkValidity())){showToast(tr("请输入有效的收件邮箱。","Enter a valid recipient email."));return;}
  try{localStorage.setItem("chemwatch-subscription",JSON.stringify(c));showToast(tr("偏好已保存。复制指令即可配置监测。","Preferences saved. Copy the instructions to configure monitoring."));}
  catch{showToast(tr("浏览器存储不可用，仍可复制指令。","Browser storage is unavailable. You can still copy the instructions."));}
}
async function copyCommand(){
  try{await navigator.clipboard.writeText($("#command").textContent);showToast(tr("指令已复制。","Instructions copied."));}
  catch{const range=document.createRange();range.selectNodeContents($("#command"));getSelection().removeAllRanges();getSelection().addRange(range);showToast(tr("指令已选中，可手动复制。","Instructions selected. Copy them manually."));}
}
async function init(){
  route();
  try{
    const [data,obs,hist,copy]=await Promise.all([readPublicData("catalog"),readPublicData("observations").catch(()=>null),readPublicData("history").catch(()=>null),readPublicData("catalog-en").catch(()=>({}))]);
    if(data.schema_version!=="1.0")throw Error(tr("不支持的目录版本","Unsupported catalog version"));
    catalog=data; observations=obs; snapshots=hist; translations=copy;
    renderOverview();setupConnect();renderCatalog();loadTimeline();loadInbox();
    $("#coverage-mode").onchange=renderCoverage;
    ["#search","#kind","#origin","#target"].forEach(id=>$(id).oninput=renderCatalog);
    $("#reset").onclick=()=>{activeTopic="";["#search","#kind","#origin","#target"].forEach(id=>$(id).value="");renderCatalog();};
    $("#export").onclick=()=>download({...catalog,entries:getResults(),export_filter:{topic:activeTopic,search:$("#search").value,kind:$("#kind").value,origin:$("#origin").value,target:$("#target").value}},"chemwatch-selection.json");
    $("#save-subscription").onclick=saveSubscription;$("#copy-command").onclick=copyCommand;
  }catch(e){$("#error").hidden=false;$("#error").textContent=tr("目录无法加载。","Could not load the catalog. ")+e.message;}
}
document.addEventListener("chemwatch-language",()=>{
  if(!catalog)return;
  renderOverview();renderCatalog();
  $$("#subscribe-topics label").forEach(label=>label.querySelector("span").textContent=topicName(label.querySelector("input").value));
  renderCommand();
  if(seriesData)renderTimeControls();
  if(discoveryData)renderInbox();
});
window.addEventListener("hashchange",route);
init();

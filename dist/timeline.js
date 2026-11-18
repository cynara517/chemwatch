"use strict";
const seriesInfo={
  csd:{name:["CSD 晶体结构","CSD structures"],unit:["条结构","structures"],color:"#67ceff"},
  chembl:{name:["ChEMBL 活性记录","ChEMBL activities"],unit:["条活性记录","activity records"],color:"#64dfbd"},
  materials:{name:["Materials Cloud 存档","Materials Cloud"],unit:["个数据集 DOI","dataset DOIs"],color:"#b39bff"},
  dataset:{name:["已收录数据集家族","Dataset families"],unit:["个家族","families"],color:"#ffb575"},
  benchmark:{name:["已收录评估套件","Benchmark suites"],unit:["个套件","suites"],color:"#f58cbc"},
  openreview:{name:["OpenReview 公开投稿","OpenReview submissions"],unit:["篇投稿","submissions"],color:"#9ada8b"}
};
let openreviewSnapshot, seriesData, selectedSeries="csd", timeMode="total", discoveryData;
const fmt=n=>n==null?tr("缺测","No data"):number(n);
function topicOptions(target,topics,includeAll){
  const select=$(target),value=select.value;
  select.replaceChildren(...(includeAll?["",...topics]:topics).map(id=>new Option(topicName(id),id)));
  if([...select.options].some(opt=>opt.value===value)) select.value=value;
}

async function readPublicData(name) {
  const response = await fetch("data/"+name+".json", {cache:"no-cache"});
  if (!response.ok) throw Error("HTTP "+response.status);
  return response.json();
}

function submissionPoints(topic) {
  if (!openreviewSnapshot?.last_success) return [];
  const byYear = new Map();
  for (const item of openreviewSnapshot.items) {
    if (!item.date || (topic && !item.topics.includes(topic) &&
        !(topic==="bioprocess" && item.topics.some(t=>t==="penicillin" || t==="erythromycin")))) continue;
    const year=Number(item.date.slice(0,4));
    if (!byYear.has(year)) byYear.set(year,[]);
    byYear.get(year).push({label:item.title,url:item.url});
  }
  if (!byYear.size) return [];
  const end=Number(openreviewSnapshot.last_success.slice(0,4)), points=[];
  let total=0;
  for (let year=Math.min(...byYear.keys());year<=end;year++) {
    const sources=byYear.get(year)||[];
    total+=sources.length;
    points.push({year,annual:sources.length,total,sources,partial:year===end});
  }
  return points;
}

function pointsFor(id, topic="") {
  if (id==="openreview") return submissionPoints(topic);
  if (id==="dataset" || id==="benchmark") return seriesData.publications[id][topic] || [];
  return seriesData[id]?.points || [];
}

function sparkline(points){
  if(points.length<2)return "";
  const first=points[0].year,last=points.at(-1).year;
  const min=Math.min(...points.map(p=>p.total)),range=Math.max(1,...points.map(p=>p.total-min));
  const line=points.map((p,i)=>{
    const command=i && p.year===points[i-1].year+1?"L":"M";
    return command+((p.year-first)*48/(last-first)).toFixed(1)+" "+(18-(p.total-min)*16/range).toFixed(1);
  }).join(" ");
  return `<svg class="spark" viewBox="-1 0 50 20" aria-hidden="true"><path d="${line}"/></svg>`;
}
function renderTimeControls(){
  topicOptions("#time-topic",Object.keys(topicsById),true);
  $("#series-picker").innerHTML=Object.entries(seriesInfo).map(([id,info])=>{
    const points=pointsFor(id),last=points.at(-1);
    return `<button data-series="${id}" aria-pressed="${id===selectedSeries}" style="--accent:${info.color}"><span class="metric-name">${tr(...info.name)}</span><strong>${fmt(last?.total)}</strong><span class="metric-foot"><small>${last?last.year+" · "+tr(...info.unit):tr("暂无观测","No observations")}</small>${sparkline(points)}</span></button>`;
  }).join("");
  $$("#series-picker button").forEach(b=>b.onclick=()=>{selectedSeries=b.dataset.series;renderTimeline();});
  renderTimeline();
}
async function loadTimeline(){
  try{
    [seriesData,openreviewSnapshot]=await Promise.all([readPublicData("timeseries"),readPublicData("openreview").catch(()=>null)]);
    const initial=new URLSearchParams(location.search);
    if(Object.hasOwn(seriesInfo,initial.get("series")))selectedSeries=initial.get("series");
    topicOptions("#time-topic",Object.keys(topicsById),true);
    if(Object.hasOwn(topicsById,initial.get("topic")))$("#time-topic").value=initial.get("topic");
    $$("[data-time-mode]").forEach(b=>b.onclick=()=>{timeMode=b.dataset.timeMode;renderTimeline();});
    $("#time-topic").onchange=renderTimeline;
    renderTimeControls();
    let width=0;
    new ResizeObserver(entries=>{
      const next=Math.round(entries[0].contentRect.width);
      if(next>0 && next!==width){width=next;renderTimeline();}
    }).observe($("#time-plot"));
  }catch(e){$("#time-plot").textContent=tr("历史数据无法加载。","Could not load historical data. ")+e.message;}
}
function sourceLinks(point,limit=Infinity){
  const sources=point.sources||[{label:tr("CCDC 年度统计表","CCDC annual statistics"),url:seriesData.csd.url}];
  const extra=sources.length>limit?tr(" · 另 "+(sources.length-limit)+" 项，见逐年表"," · "+(sources.length-limit)+" more in the table"):"";
  return sources.slice(0,limit).map(s=>{
    const label=language==="en"?sourceName(s.label).replace(/(\d{4}) 年 DOI/g,"$1 DOIs"):s.label;
    return `<a href="${escapeHTML(s.url)}" target="_blank" rel="noopener">${escapeHTML(label)} ↗</a>`;
  }).join(" · ")+extra;
}
function seriesNote(id){
  if(id==="openreview")return tr(
    "公开可见的投稿主帖按创建年归档，每个 forum ID 计一次。同稿跨场次可有多个主帖，覆盖范围取决于检索词与公开状态。",
    "Public submission threads by creation year. Each forum ID counts once. Separate venue submissions can represent the same work. Coverage follows the title queries and visibility."
  )+" "+(openreviewSnapshot?.last_success?tr("最近成功采集","Last successful check")+" · "+openreviewSnapshot.last_success.slice(0,10):tr("尚无成功采集。","No successful collection."))+
    (openreviewSnapshot?.error?tr("。最近检查失败，显示上次快照。",". Latest check failed. Showing the previous snapshot."):"");
  if(id==="csd")return tr(
    `CCDC ${seriesData.csd?.edition||""} 年版按结构发表年份统计。累计含 1923–1964 年的 ${fmt(seriesData.csd?.baseline)} 条早期记录。空心点表示末两年的部分数据。`,
    `CCDC ${seriesData.csd?.edition||""} edition, grouped by publication year. Totals include ${fmt(seriesData.csd?.baseline)} structures from 1923–1964. Hollow points mark the two incomplete years.`
  );
  if(id==="materials")return tr("按 DataCite 仓库 ethz.marvel 的 Dataset DOI 发表年统计。逐年之和与整库总数核对。不同版本可各有 DOI，末年数据仍在更新。","Dataset DOIs by publication year in the DataCite repository ethz.marvel. Annual counts reconcile with the repository total. Editions may have separate DOIs. The final year is incomplete.");
  if(id==="chembl")return tr("每年取 EMBL-EBI 最后一个已解析版本的活性记录数。年度净变动含订正，仅比较连续两年的快照。缺少版本的年份留空。","Activity records in the last parsed EMBL-EBI release of each year. Annual net change includes corrections and requires consecutive yearly snapshots. Gaps indicate missing releases.");
  return tr("按本目录可核实的最早论文、挑战或版本年份统计，同一家族的版本与镜像合并。0 表示当年暂无已收录新增资源，后续补录可修订历史。","Earliest verified paper, challenge or release in this catalog. Editions and mirrors share a family. A zero means no additions in current coverage. Historical counts can change as sources are reviewed.");
}

function renderTimeline() {
  const id=selectedSeries, isCatalog=id==="dataset"||id==="benchmark";
  const supportsTopics=isCatalog || id==="openreview";
  const topic=supportsTopics?$("#time-topic").value:"";
  const points=pointsFor(id,topic), annual=timeMode==="annual", log=timeMode==="log";
  const info=seriesInfo[id],metric=annual?"annual":"total",unit=tr(...info.unit);
  $("#timeline").style.setProperty("--chart-color",info.color);
  $("#time-title").textContent=tr(...info.name)+(topic?" · "+topicName(topic):"");
  const viewName=annual?(id==="chembl"?tr("年度净变动","Annual net change"):tr("年度","Annual")):
    log?tr("累计 · 对数坐标","Cumulative · log scale"):tr("累计","Cumulative");
  $("#time-unit").textContent=viewName+" / "+unit+(points.length?"　·　"+points[0].year+"–"+points.at(-1).year:"");
  $("#time-topic-label").hidden=!supportsTopics;
  $$("[data-series]").forEach(b=>b.setAttribute("aria-pressed",b.dataset.series===id));
  $$("[data-time-mode]").forEach(b=>b.setAttribute("aria-pressed",b.dataset.timeMode===timeMode));
  const errors=(seriesData.errors||[]).filter(e=>id==="csd"?e.startsWith("CSD"):id==="chembl"?/chembl/i.test(e):id==="materials"?e.startsWith("DataCite"):false);
  $("#time-note").textContent=seriesNote(id)+(errors.length?tr(" 采集缺口 · "," Collection gaps · ")+errors.join(" / "):"");
  $("#time-point").textContent="";
  if(!points.length){
    $("#time-plot").textContent=id==="openreview"&&openreviewSnapshot?.last_success?
      tr("当前检索范围内，该专题有创建日期的投稿为 0 篇。","No dated submissions match this topic in the current search."):
      tr("这个专题尚无可核实年份的条目。","No verified dates are available for this selection.");
    $("#time-details").hidden=true;return;
  }
  $("#time-details").hidden=false;
  const headers=[tr("年份","Year"),id==="chembl"?tr("年度净变动","Net change"):tr("年度","Annual"),tr("累计","Cumulative"),tr("依据","Evidence")];
  $("#time-table").innerHTML="<table><thead><tr>"+headers.map(s=>"<th>"+s+"</th>").join("")+"</tr></thead><tbody>"+
    [...points].reverse().map(p=>`<tr><td>${p.year}${p.partial?" *":""}</td><td>${fmt(p.annual)}</td><td>${fmt(p.total)}</td><td>${sourceLinks(p)||"—"}</td></tr>`).join("")+"</tbody></table>";
  const plot=$("#time-plot"), w=Math.max(280,plot.clientWidth), h=w<600?237:292;
  const left=w<480?49:67, right=w-20, top=22, bottom=h-31;
  const values=points.map(p=>p[metric]).filter(n=>n!=null && (!log || n>0));
  if(!values.length){plot.textContent=tr("暂无可比较的观测。","No comparable observations.");return;}
  const lo=log?10**Math.floor(Math.log10(Math.min(...values))):Math.min(0,...values);
  const hi=log?Math.max(lo*10,10**Math.ceil(Math.log10(Math.max(...values)))):Math.max(1,...values);
  const first=points[0].year,last=points.at(-1).year;
  const x=year=>first===last?(left+right)/2:left+(right-left)*(year-first)/(last-first);
  const y=num=>bottom-(bottom-top)*(log?(Math.log10(num)-Math.log10(lo))/(Math.log10(hi)-Math.log10(lo)):(num-lo)/(hi-lo));
  const ticks=log?Array.from({length:Math.round(Math.log10(hi)-Math.log10(lo))+1},(_,i)=>lo*10**i):[...new Set(Array.from({length:5},(_,i)=>Math.round(lo+(hi-lo)*i/4)))];
  const compact=new Intl.NumberFormat(locale(),{notation:"compact",maximumFractionDigits:1});
  let svg=ticks.map(n=>`<line x1="${left}" y1="${y(n)}" x2="${right}" y2="${y(n)}"/><text x="${left-8}" y="${y(n)+4}" text-anchor="end">${compact.format(n)}</text>`).join("");
  const slots=Math.min(w<520?4:8,last-first+1);
  const years=Array.from({length:slots},(_,i)=>slots===1?first:Math.round(first+(last-first)*i/(slots-1)));
  svg+=years.map(yr=>`<text x="${x(yr)}" y="${bottom+23}" text-anchor="middle">${yr}</text>`).join("");
  let path="",dots="",prev=null,areas=[],segment=[];
  points.forEach(p=>{
    const n=p[metric];
    if(n==null || (log && n<=0)){prev=null;return;}
    if(prev!==p.year-1){segment=[];areas.push(segment);}
    segment.push([x(p.year),y(n)]);
    path+=(prev===p.year-1?" L":" M")+x(p.year)+" "+y(n);
    prev=p.year;
    dots+=`<circle cx="${x(p.year)}" cy="${y(n)}" r="${p.partial?4:2.6}" class="${p.partial?"partial":""}"/>`;
  });
  const fills = areas.map(s=>`<path class="area" d="M${s[0][0]} ${bottom} ${s.map(p=>"L"+p.join(" ")).join(" ")} L${s.at(-1)[0]} ${bottom}Z"/>`).join("");
  const title=escapeHTML($("#time-title").textContent+" · "+$("#time-unit").textContent);
  plot.innerHTML=`<svg tabindex="0" role="img" aria-label="${title} · ${tr("用左右方向键查看年份","Use the arrow keys to explore years")}" viewBox="0 0 ${w} ${h}"><title>${title}</title><defs><linearGradient id="area-fill" x1="0" x2="0" y1="0" y2="1" gradientUnits="objectBoundingBox"><stop offset="0%" stop-color="${info.color}" stop-opacity=".24"/><stop offset="100%" stop-color="${info.color}" stop-opacity=".015"/></linearGradient></defs>${svg}${fills}<path class="trend" d="${path}"/>${dots}<line id="cursor-line" y1="${top}" y2="${bottom}"/></svg>`;
  let index=points.length-1;
  function show(i){
    index=Math.max(0,Math.min(i,points.length-1));
    const p=points[index],pos=x(p.year);
    $("#cursor-line").setAttribute("x1",pos);$("#cursor-line").setAttribute("x2",pos);
    $("#time-point").innerHTML=`<b>${p.year}${p.partial?" *":""}</b>　${fmt(p[metric])} ${unit}　${sourceLinks(p,2)}`;
  }
  const graph=plot.firstElementChild;
  graph.onpointermove=e=>{
    const box=graph.getBoundingClientRect(), at=(e.clientX-box.left)*w/box.width;
    const year=Math.round(first+(at-left)/(right-left)*(last-first));
    const i=points.findIndex(p=>p.year===year);
    if(year<first || year>last)return;
    if(i<0){$("#time-point").textContent=year+" · "+tr("缺少版本快照","No release snapshot");return;}
    show(i);
  };
  graph.onkeydown=e=>{if(["ArrowLeft","ArrowRight"].includes(e.key)){e.preventDefault();show(index+(e.key==="ArrowLeft"?-1:1));}};
  show(index);
}

function renderInbox(){
  topicOptions("#inbox-topic",[...TOPICS,...EXTRA].filter(t=>t.id!=="bioprocess").map(t=>t.id),false);
  const f=discoveryData.feeds[$("#inbox-platform").value+"/"+$("#inbox-topic").value];
  if(!f){$("#inbox-list").textContent=tr("尚无此项检索。","This query has no observations.");return;}
  const status=f.error?tr("本次检查失败，显示上次结果。","Latest check failed. Showing the last successful results."):tr("检索完成","Search complete");
  $("#inbox-list").innerHTML=`<p>${status} · ${f.last_success?escapeHTML(f.last_success.slice(0,10)):tr("尚无成功记录","No successful check")} ${f.query_url?` · <a href="${escapeHTML(f.query_url)}" target="_blank" rel="noopener">${tr("查询依据","View query")} ↗</a>`:""}</p><ul>${f.items.map(i=>{
    const metadata=i.forum?[i.venue,i.date&&tr("建帖 ","Created ")+i.date,i.public_date&&tr("公开 ","Public ")+i.public_date].filter(Boolean).join(" · "):i.date?.slice(0,10);
    return `<li><a href="${escapeHTML(i.url)}" target="_blank" rel="noopener">${escapeHTML(i.title)} ↗</a> <small>${escapeHTML(metadata||"")}</small></li>`;
  }).join("")}</ul>`+(f.items.length?"":tr("此查询暂无候选。","No candidates for this query."));
}
async function loadInbox(){
  try {
    discoveryData=await readPublicData("discovery");
    $("#inbox-platform").onchange=renderInbox;$("#inbox-topic").onchange=renderInbox;renderInbox();
  }catch(e){$("#inbox-list").textContent=tr("检索结果暂时无法读取。","Search results are temporarily unavailable.");}
}

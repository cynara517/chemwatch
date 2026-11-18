"use strict";
const seriesNames = {dataset:"数据集家族", benchmark:"Benchmark 套件", csd:"CSD 晶体结构", chembl:"ChEMBL 活性记录"};
const seriesUnits = {dataset:"个家族",benchmark:"个套件",csd:"条结构",chembl:"条活性记录"};
let seriesData, selectedSeries="dataset", timeMode="total", discoveryData;
const fmt = n => n == null ? "缺测" : n.toLocaleString("zh-CN");

async function readPublicData(name) {
  const response = await fetch("data/"+name+".json", {cache:"no-cache"});
  if (!response.ok) throw Error("HTTP "+response.status);
  return response.json();
}

function pointsFor(id, topic="") {
  if (id==="dataset" || id==="benchmark") return seriesData.publications[id][topic] || [];
  return seriesData[id]?.points || [];
}

async function loadTimeline() {
  try {
    seriesData = await readPublicData("timeseries");
    $("#time-topic").innerHTML = [{id:"",name:"全部方向"},...TOPICS,...EXTRA].map(t=>`<option value="${t.id}">${t.name}</option>`).join("");
    $("#series-picker").innerHTML = Object.entries(seriesNames).map(([id,name])=>{
      const last=pointsFor(id).at(-1);
      return `<button data-series="${id}" aria-pressed="${id===selectedSeries}"><span>${name}</span><strong>${fmt(last?.total)}</strong><small>${last ? last.year+" 年 · "+seriesUnits[id] : "暂无观测"}</small></button>`;
    }).join("");
    $$("#series-picker button").forEach(b=>b.onclick=()=>{selectedSeries=b.dataset.series; renderTimeline();});
    $$("[data-time-mode]").forEach(b=>b.onclick=()=>{timeMode=b.dataset.timeMode;renderTimeline();});
    $("#time-topic").onchange=renderTimeline;
    let width=0;
    new ResizeObserver(entries=>{
      const next=Math.round(entries[0].contentRect.width);
      if (next>0 && next!==width){width=next;renderTimeline();}
    }).observe($("#time-plot"));
    renderTimeline();
  } catch(e) {$("#time-plot").textContent="读取历史数据失败："+e.message;}
}

function sourceLinks(point) {
  const sources = point.sources || [{label:"CCDC 年度统计表",url:seriesData.csd.url}];
  return sources.map(s=>`<a href="${escapeHTML(s.url)}" target="_blank" rel="noopener">${escapeHTML(s.label)} ↗</a>`).join(" · ");
}

function renderTimeline() {
  const id=selectedSeries, isCatalog=id==="dataset"||id==="benchmark";
  const topic=isCatalog?$("#time-topic").value:"";
  const points=pointsFor(id,topic), annual=timeMode==="annual", log=timeMode==="log";
  const metric=annual?"annual":"total", unit=seriesUnits[id];
  $("#time-title").textContent=seriesNames[id]+(topic?" · "+LABELS[topic]:"");
  $("#time-unit").textContent=(annual?(id==="chembl"?"年度净变动":"年度数量"):log?"累计数量 · 对数坐标":"累计数量")+" / "+unit;
  $("#time-topic-label").hidden=!isCatalog;
  $$("[data-series]").forEach(b=>b.setAttribute("aria-pressed",b.dataset.series===id));
  $$("[data-time-mode]").forEach(b=>b.setAttribute("aria-pressed",b.dataset.timeMode===timeMode));
  const notes=isCatalog?"按本目录中可核实的最早论文、挑战或版本年份统计。家族内的版本和镜像合并。0 表示该年在当前收录范围内无新增，补录可改写历史。":id==="csd"?
    `CCDC ${seriesData.csd?.edition||""} 年版按结构发表年份回溯。累计含 1923–1964 年合计 ${fmt(seriesData.csd?.baseline)} 条；末两年为截至该版的部分数据。`:
    "每年取 EMBL-EBI 最后一个已解析版本的 activities 总数；年度值为相邻两年快照净差，可含订正。缺版年份保留空档。";
  const errors=(seriesData.errors||[]).filter(e=>id==="csd"?e.startsWith("CSD"):id==="chembl"?/chembl/i.test(e):false);
  $("#time-note").textContent=notes+(errors.length?" 最近采集有缺口："+errors.join(" / "):"");
  $("#time-point").textContent="";
  if(!points.length){
    $("#time-plot").innerHTML='<p class="empty">这个专题尚无可核实年份的条目。</p>';$("#time-details").hidden=true;return;
  }
  $("#time-details").hidden=false;
  $("#time-table").innerHTML='<table><thead><tr><th>年份</th><th>年度'+(id==="chembl"?"净变动":"")+'</th><th>累计</th><th>依据</th></tr></thead><tbody>'+
    [...points].reverse().map(p=>`<tr><td>${p.year}${p.partial?" *":""}</td><td>${fmt(p.annual)}</td><td>${fmt(p.total)}</td><td>${sourceLinks(p)||"—"}</td></tr>`).join("")+"</tbody></table>";
  const plot=$("#time-plot"), w=Math.max(280,plot.clientWidth), h=245;
  const left=w<480?49:67, right=w-20, top=15, bottom=h-35;
  const values=points.map(p=>p[metric]).filter(n=>n!=null && (!log || n>0));
  if(!values.length){plot.textContent="该口径暂无可比较的观测。";return;}
  const lo=log?10**Math.floor(Math.log10(Math.min(...values))):Math.min(0,...values);
  const hi=log?Math.max(lo*10,10**Math.ceil(Math.log10(Math.max(...values)))):Math.max(1,...values);
  const first=points[0].year,last=points.at(-1).year;
  const x=year=>first===last?(left+right)/2:left+(right-left)*(year-first)/(last-first);
  const y=num=>bottom-(bottom-top)*(log?(Math.log10(num)-Math.log10(lo))/(Math.log10(hi)-Math.log10(lo)):(num-lo)/(hi-lo));
  const ticks=log?Array.from({length:Math.round(Math.log10(hi)-Math.log10(lo))+1},(_,i)=>lo*10**i):[...new Set(Array.from({length:5},(_,i)=>Math.round(lo+(hi-lo)*i/4)))];
  const compact=new Intl.NumberFormat("zh-CN",{notation:"compact",maximumFractionDigits:1});
  let svg=ticks.map(n=>`<line x1="${left}" y1="${y(n)}" x2="${right}" y2="${y(n)}"/><text x="${left-8}" y="${y(n)+4}" text-anchor="end">${compact.format(n)}</text>`).join("");
  const slots=Math.min(w<520?4:8,last-first+1);
  const years=Array.from({length:slots},(_,i)=>slots===1?first:Math.round(first+(last-first)*i/(slots-1)));
  svg+=years.map(yr=>`<text x="${x(yr)}" y="${bottom+23}" text-anchor="middle">${yr}</text>`).join("");
  let path="",dots="",prev=null;
  points.forEach(p=>{
    const n=p[metric];
    if(n==null || (log && n<=0)){prev=null;return;}
    path+=(prev===p.year-1?" L":" M")+x(p.year)+" "+y(n);
    prev=p.year;
    dots+=`<circle cx="${x(p.year)}" cy="${y(n)}" r="${p.partial?4:2.6}" class="${p.partial?"partial":""}"/>`;
  });
  const title=escapeHTML($("#time-title").textContent+" · "+$("#time-unit").textContent);
  plot.innerHTML=`<svg tabindex="0" role="img" aria-label="${title}，左右方向键查看各年" viewBox="0 0 ${w} ${h}"><title>${title}</title>${svg}<path d="${path}"/>${dots}<line id="cursor-line" y1="${top}" y2="${bottom}"/></svg>`;
  let index=points.length-1;
  function show(i){
    index=Math.max(0,Math.min(i,points.length-1));
    const p=points[index],pos=x(p.year);
    $("#cursor-line").setAttribute("x1",pos);$("#cursor-line").setAttribute("x2",pos);
    $("#time-point").innerHTML=`<b>${p.year}${p.partial?" *":""}</b>　${fmt(p[metric])} ${unit}　${sourceLinks(p)}`;
  }
  const graph=plot.firstElementChild;
  graph.onpointermove=e=>{
    const box=graph.getBoundingClientRect(), at=(e.clientX-box.left)*w/box.width;
    const year=Math.round(first+(at-left)/(right-left)*(last-first));
    const i=points.findIndex(p=>p.year===year);
    if(year<first || year>last)return;
    if(i<0){$("#time-point").textContent=year+" · 缺少版本快照";return;}
    show(i);
  };
  graph.onkeydown=e=>{if(["ArrowLeft","ArrowRight"].includes(e.key)){e.preventDefault();show(index+(e.key==="ArrowLeft"?-1:1));}};
  show(index);
}

async function loadInbox(){
  try {
    discoveryData=await readPublicData("discovery");
    $("#inbox-topic").innerHTML=[...TOPICS,...EXTRA].filter(t=>t.id!=="bioprocess").map(t=>`<option value="${t.id}">${t.name}</option>`).join("");
    function display(){
      const f=discoveryData.feeds[$("#inbox-platform").value+"/"+$("#inbox-topic").value];
      if(!f){$("#inbox-list").textContent="尚无此项检索。";return;}
      const status=f.error?"本次检查失败，保留上次成功结果。":"本次检索完成。";
      $("#inbox-list").innerHTML=`<p>${status} ${f.last_success?"数据时间 "+escapeHTML(f.last_success.slice(0,10)):"尚无成功记录"} · ${f.query_url?`<a href="${escapeHTML(f.query_url)}" target="_blank" rel="noopener">核对查询 ↗</a>`:""}</p><ul>${f.items.map(i=>`<li><a href="${escapeHTML(i.url)}" target="_blank" rel="noopener">${escapeHTML(i.title)} ↗</a> <small>${escapeHTML(i.date?.slice(0,10)||"")}</small></li>`).join("")}</ul>`+(f.items.length?"":"此查询暂无候选。");
    }
    $("#inbox-platform").onchange=display;$("#inbox-topic").onchange=display;display();
  }catch(e){$("#inbox-list").textContent="候选检索结果暂时无法读取。";}
}

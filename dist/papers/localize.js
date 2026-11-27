/* Translate complete, reviewed Chinese passages without changing their markup. */
(()=>{
  const originals=new WeakMap();
  function english(text){
    if(window.paperEnglish[text])return window.paperEnglish[text];
    let match=text.match(/^显示 (\d+) \/ (\d+) 项$/);
    if(match)return `Showing ${match[1]} / ${match[2]} publications`;
    match=text.match(/^(\d+) 项成果$/);
    if(match)return `${match[1]} publication${match[1]==='1'?'':'s'}`;
    return text;
  }
  window.localizePapers=()=>{
    const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
    while(walker.nextNode()){
      const node=walker.currentNode;
      if(node.parentElement.closest('script,style,[data-en]'))continue;
      if(!originals.has(node))originals.set(node,node.nodeValue);
      const original=originals.get(node),core=original.trim();
      node.nodeValue=language==='en'?original.replace(core,english(core)):original;
    }
    for(const el of document.querySelectorAll('[alt],[aria-label],[placeholder],meta[name="description"]')){
      if(!originals.has(el))originals.set(el,{});
      const saved=originals.get(el);
      for(const attr of ['alt','aria-label','placeholder','content'])if(el.hasAttribute(attr)&&!el.hasAttribute({'alt':'data-en-alt','aria-label':'data-en-aria','placeholder':'data-en-placeholder','content':'data-en-content'}[attr])){
        if(!(attr in saved))saved[attr]=el.getAttribute(attr);
        el.setAttribute(attr,language==='en'?english(saved[attr]):saved[attr]);
      }
    }
    if(language==='en')document.title=document.title.replace('本科探索 · 研究的起点','Undergraduate explorations').replace('研究档案','Research story');
    window.carrySiteLanguage?.();
  };
})();

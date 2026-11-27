/* Keep language explicit across all three sections, even without local storage. */
(()=>{
  window.carrySiteLanguage=()=>{
    for(const link of document.querySelectorAll('a[href]')){
      const href=link.getAttribute('href');
      if(!href||href.startsWith('#')||link.hasAttribute('download'))continue;
      const target=new URL(href,location.href);
      if(target.origin!==location.origin||!target.pathname.endsWith('.html'))continue;
      target.searchParams.set('lang',language);link.href=target.href;
    }
  };
  carrySiteLanguage();
  document.addEventListener('chemwatch-language',carrySiteLanguage);
})();

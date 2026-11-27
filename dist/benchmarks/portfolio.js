"use strict";
// Use the parent site's language preference, and carry it across file/HTTP links.
function carryPortfolioLanguage() {
  for (const link of document.querySelectorAll('a[href]')) {
    const original=link.getAttribute('href');
    if (!original || original.startsWith('#') || link.hasAttribute('download')) continue;
    const target=new URL(original,location.href);
    if (target.origin!==location.origin || !target.pathname.endsWith('.html')) continue;
    target.searchParams.set('lang',language);
    link.href=target.href;
  }
}
carryPortfolioLanguage();
document.addEventListener('chemwatch-language',carryPortfolioLanguage);

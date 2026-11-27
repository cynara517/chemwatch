"use strict";
const languageKey = "chemwatch-language";
const supportedLanguage = lang => ["zh","en"].includes(lang);
function initialLanguage() {
  const requested=new URLSearchParams(location.search).get("lang");
  if (supportedLanguage(requested)) return requested;
  try {
    const saved=localStorage.getItem(languageKey);
    if (supportedLanguage(saved)) return saved;
  } catch {}
  return navigator.language?.toLowerCase().startsWith("en") ? "en" : "zh";
}

let language=initialLanguage();
const tr=(zh,en)=>language==="en"?en:zh;
const locale=()=>tr("zh-CN","en-US");
const staticCopy=[];
for (const [key,attribute] of [["en",null],["enAria","aria-label"],["enPlaceholder","placeholder"],["enContent","content"],["enAlt","alt"]]) {
  const selector="[data-"+key.replace(/[A-Z]/g,c=>"-"+c.toLowerCase())+"]";
  for (const element of document.querySelectorAll(selector)) {
    staticCopy.push({element,attribute,zh:attribute?element.getAttribute(attribute):element.textContent,en:element.dataset[key]});
  }
}
function translatePage() {
  document.documentElement.lang=locale();
  for (const {element,attribute,zh,en} of staticCopy) {
    if (attribute) element.setAttribute(attribute,tr(zh,en));
    else element.textContent=tr(zh,en);
  }
  document.querySelectorAll("[data-lang]").forEach(button=>button.setAttribute("aria-pressed",String(button.dataset.lang===language)));
}
translatePage();
for (const button of document.querySelectorAll("[data-lang]")) {
  button.addEventListener("click",()=>{
    if (language===button.dataset.lang) return;
    language=button.dataset.lang;
    const url=new URL(location.href);
    url.searchParams.set("lang",language);
    window.history.replaceState(null,"",url);
    try { localStorage.setItem(languageKey,language); } catch {}
    translatePage();
    document.dispatchEvent(new Event("chemwatch-language"));
  });
}

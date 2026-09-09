let current;
chrome.tabs.query({active:true,currentWindow:true}).then(([tab])=>{current=tab;document.querySelector('#page').textContent=tab?.title||'Upload a video in the studio.';});
function openStudio(source='') {
 chrome.runtime.sendMessage({type:'open-studio',source}, response=>{
  if(chrome.runtime.lastError||!response?.ok) document.querySelector('#page').textContent='The ClipForge companion is not installed. Run Install ClipForge once.';
  else window.close();
 });
}
document.querySelector('#open').onclick=()=>openStudio();
document.querySelector('#import').onclick=async()=>{
 let source=current?.url||'';
 if(!/^https?:/.test(source)){document.querySelector('#page').textContent='Open a video page first, or use Upload in the studio.';return;}
 if(!/youtube\.com|youtu\.be/.test(new URL(source).hostname)){
  try {const [r]=await chrome.scripting.executeScript({target:{tabId:current.id},func:()=>Array.from(document.querySelectorAll('video')).map(v=>v.currentSrc||v.src).find(s=>/^https?:/.test(s))});if(r?.result)source=r.result;}catch{}
 }
 openStudio(source);
};

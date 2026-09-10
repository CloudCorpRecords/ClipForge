chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({id:'clipforge',title:'Create clips with ClipForge',contexts:['page','video','link']});
});

let nativePort=null;
let engineReady=false;
let startPromise=null;

function ensureEngine() {
  if (startPromise) return startPromise;
  startPromise = Promise.resolve().then(async () => {
    if (engineReady && nativePort) {
      try {
        const response = await fetch('http://127.0.0.1:43177/api/health', {signal:AbortSignal.timeout(3000)});
        if (response.ok && (await response.json()).ok) return {ok:true,alreadyRunning:true};
      } catch {}
      const stale = nativePort;
      nativePort = null;
      engineReady = false;
      stale.disconnect();
    }
    return new Promise((resolve, reject) => {
      const port = chrome.runtime.connectNative('com.clipforge.engine');
      nativePort = port;
      const timer = setTimeout(() => { port.disconnect(); reject(new Error('The editing engine took too long to start. Check data/engine.log.')); }, 35000);
      port.onMessage.addListener(response => {
        clearTimeout(timer);
        if (response?.ok) { engineReady = true; resolve(response); }
        else { port.disconnect(); reject(new Error(response?.error || 'ClipForge engine did not start.')); }
      });
      port.onDisconnect.addListener(() => {
        clearTimeout(timer);
        const message = chrome.runtime.lastError?.message || 'ClipForge companion disconnected.';
        if (nativePort === port) { engineReady = false; nativePort = null; }
        reject(new Error(message));
      });
      port.postMessage({action:'start'});
    });
  }).finally(() => { startPromise = null; });
  return startPromise;
}

function studioUrl(source='') {
  const url = new URL(chrome.runtime.getURL('studio/index.html'));
  if (source) url.searchParams.set('source', source);
  return url.href;
}

async function openStudio(source='') {
  try { await ensureEngine(); }
  catch (error) { console.error('ClipForge engine:', error); }
  return chrome.tabs.create({url:studioUrl(source)});
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === 'ensure-engine') {
    ensureEngine().then(sendResponse).catch(error => sendResponse({ok:false,error:error.message}));
    return true;
  }
  if (message?.type === 'open-studio') {
    openStudio(message.source || '').then(tab => sendResponse({ok:true,tabId:tab.id})).catch(error => sendResponse({ok:false,error:error.message}));
    return true;
  }
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  const source=info.srcUrl || info.linkUrl || tab?.url || '';
  openStudio(source);
});

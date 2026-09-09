chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({id:'clipforge',title:'Create clips with ClipForge',contexts:['page','video','link']});
});

let nativePort=null;
let engineReady=false;
let startPromise=null;

function ensureEngine() {
  if (engineReady && nativePort) return Promise.resolve({ok:true,alreadyRunning:true});
  if (startPromise) return startPromise;
  startPromise = new Promise((resolve, reject) => {
    try {
      nativePort = chrome.runtime.connectNative('com.clipforge.engine');
      nativePort.onMessage.addListener(response => {
        startPromise=null;
        if (response?.ok) { engineReady=true; resolve(response); }
        else reject(new Error(response?.error || 'ClipForge engine did not start.'));
      });
      nativePort.onDisconnect.addListener(() => {
        const message=chrome.runtime.lastError?.message || 'ClipForge companion disconnected.';
        engineReady=false;
        nativePort=null;
        if (startPromise) { startPromise=null; reject(new Error(message)); }
      });
      nativePort.postMessage({action:'start'});
    } catch (error) {
      startPromise=null;
      reject(error);
    }
  });
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

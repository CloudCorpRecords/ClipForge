const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
test('restarts a dead engine even while native port remains connected',async()=>{
 let connects=0,healthy=false;
 const event=()=>({addListener(){}});
 const chrome={runtime:{onInstalled:event(),onMessage:event(),connectNative(){
  connects++;
  let message,disconnect;
  return {onMessage:{addListener(fn){message=fn}},onDisconnect:{addListener(fn){disconnect=fn}},postMessage(){queueMicrotask(()=>message({ok:true}))},disconnect(){disconnect?.()}};
 }},contextMenus:{onClicked:event()},tabs:{}};
 const context=vm.createContext({chrome,console,URL,setTimeout,clearTimeout,AbortSignal,fetch:async()=>{if(!healthy)throw Error('offline');return {ok:true,json:async()=>({ok:true})}}});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../extension/background.js'),'utf8'),context);
 const first=context.ensureEngine();assert.equal(first,context.ensureEngine());await first;assert.equal(connects,1);
 await context.ensureEngine();assert.equal(connects,2);
 healthy=true;await context.ensureEngine();assert.equal(connects,2);
});

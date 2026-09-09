'use strict';
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
let project=null,selected=null,count=4,currentJob=null,showingExport=false,editingWords=false,polling=false,toastTimer,ghlInfo={},ghlAccounts=[],ghlUsers=[],calCursor=new Date(),miniCursor=new Date(),pickedDay=new Date(),scheduleClip=null,activePost=null,calendarPosts=[],brand={font:'Arial',color:'#FFFFFF',highlight:'#C8ED48',style:'pop'},rangeSel=null,rangeDrag=null;
const picked=new Set();
const seenJobs=new Set();
const ENGINE='http://127.0.0.1:43177';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clock=t=>{t=Math.max(0,Number(t)||0);return `${String(Math.floor(t/60)).padStart(2,'0')}:${String(Math.floor(t%60)).padStart(2,'0')}`};
const mediaUrl=(projectId,path,download=false)=>`${ENGINE}/media/${projectId}/${path}${download?'?download=true':''}`;
const asset=(path,download=false)=>mediaUrl(project.id,path,download);
function toast(message,error=false){clearTimeout(toastTimer);$('#toast').textContent=message;$('#toast').classList.toggle('error',error);$('#toast').hidden=false;toastTimer=setTimeout(()=>$('#toast').hidden=true,error?16000:5000)}
async function api(path,body,method){
 const opts={method:method||(body===undefined?'GET':'POST'),headers:{'X-ClipForge':'1'}};
 if(body!==undefined){if(body instanceof FormData)opts.body=body;else{opts.headers['Content-Type']='application/json';opts.body=JSON.stringify(body)}}
 const r=await fetch(ENGINE+'/api'+path,opts);let value;try{value=await r.json()}catch{value={detail:'The local service returned an invalid response.'}}
 if(!r.ok)throw Error(typeof value.detail==='string'?value.detail:JSON.stringify(value.detail||value));return value;
}
const safe=fn=>async(...args)=>{try{return await fn(...args)}catch(e){toast(e.message,true)}};
function posterName(){const u=ghlUsers.find(x=>x.id===ghlInfo.user);return u?`${u.name}${u.email?' · '+u.email:''}`:''}
function fillUserSelect(id,selectedId){
 const pick=selectedId||ghlInfo.user||(ghlUsers[0]&&ghlUsers[0].id)||'';
 $(id).innerHTML=ghlUsers.length?ghlUsers.map(u=>`<option value="${esc(u.id)}" ${u.id===pick?'selected':''}>${esc(u.name)}${u.email?' · '+esc(u.email):''}</option>`).join(''):'<option value="">Test connection to load staff</option>';
}
function fillGhl(info){
 ghlInfo=info||{};$('#ghl-location').value=ghlInfo.location||'';
 fillUserSelect('#ghl-user',ghlInfo.user);
 const who=posterName();
 $('#ghl-scopes').textContent=ghlInfo.connected?(who?`● GoHighLevel connected · posting as ${who}`:`● GoHighLevel connected · location ${ghlInfo.location}`):'GoHighLevel is not connected yet.';
 $('#calendar-status').textContent=ghlInfo.connected?(who?`Posting as ${who}. Drag a post onto another day to move it.`:'Pick who is posting in Settings, then drag posts to move them.'):'Connect GoHighLevel in Settings to see every scheduled post.';
}
const PLAT={instagram:['IG','#E1306C'],facebook:['f','#1877F2'],tiktok:['TT','#111'],youtube:['▶','#FF0033'],linkedin:['in','#0A66C2'],twitter:['X','#111'],x:['X','#111'],google:['G','#34A853'],gmb:['G','#34A853'],pinterest:['P','#E60023'],threads:['@','#333'],snapchat:['SC','#FFFC00']};
function platKey(name){const s=String(name||'').toLowerCase();if(s.includes('insta'))return 'instagram';if(s.includes('face'))return 'facebook';if(s.includes('tiktok'))return 'tiktok';if(s.includes('you'))return 'youtube';if(s.includes('link'))return 'linkedin';if(s.includes('twitter')||s==='x')return 'x';if(s.includes('google')||s.includes('gmb')||s.includes('business'))return 'google';if(s.includes('pinterest'))return 'pinterest';if(s.includes('thread'))return 'threads';if(s.includes('snap'))return 'snapchat';return s.split(/[\s/_-]/)[0]||'';}
function socIcons(ids,extra){const keys=new Set();(ids||[]).forEach(id=>{const a=ghlAccounts.find(x=>x.id===id);const k=platKey(a?.platform||a?.type||a?.name);if(k)keys.add(k)});(extra||[]).forEach(p=>{const k=platKey(p);if(k)keys.add(k)});return [...keys].map(k=>{const [label,color]=PLAT[k]||[(k[0]||'?').toUpperCase(),'#556c38'];return `<i class="soc" style="background:${color}${k==='snapchat'||k==='tiktok'||k==='x'?';color:#111':''}" title="${esc(k)}">${label}</i>`}).join('')||'<i class="soc" style="background:#556c38">•</i>'}
function fillBrand(info,links){
 brand=Object.assign({font:'Arial',color:'#FFFFFF',highlight:'#C8ED48',style:'pop'},info||{});
 ['#set-font','#gen-font','#edit-font'].forEach(id=>{if($(id))$(id).value=brand.font});
 ['#set-caption-style','#gen-caption-style'].forEach(id=>{if($(id))$(id).value=brand.style});
 if($('#set-color'))$('#set-color').value=brand.color;if($('#gen-color'))$('#gen-color').value=brand.color;
 if($('#set-highlight'))$('#set-highlight').value=brand.highlight;if($('#gen-highlight'))$('#gen-highlight').value=brand.highlight;
 if($('#brand-saved'))$('#brand-saved').textContent=`Saved · ${brand.font} · ${brand.style} · ${brand.color} / ${brand.highlight}`;
 if(links){if($('#set-site'))$('#set-site').value=links.site||'https://cardpriceking.com';if($('#set-course'))$('#set-course').value=links.course||'https://cardpriceking.com/course/bulk-selling'}
 document.documentElement.style.setProperty('--cap',brand.color);document.documentElement.style.setProperty('--hi',brand.highlight);
}
function brandFields(prefix){return {caption_style:$(prefix==='edit'?'#caption-style':'#'+prefix+'-caption-style')?.value||brand.style,caption_font:$(prefix==='edit'?'#edit-font':'#'+prefix+'-font')?.value||brand.font,caption_color:($(prefix==='edit'?'#edit-color':'#'+prefix+'-color')?.value||brand.color).toUpperCase(),caption_highlight:($(prefix==='edit'?'#edit-highlight':'#'+prefix+'-highlight')?.value||brand.highlight).toUpperCase()}}
async function health(){const h=await api('/health');$('#connection').textContent='Local service connected';$('#connection').classList.remove('offline');$('#ai-model').value=h.model;$('#stt-model').value=h.stt_model;$('#key-status').textContent=h.key_set?'● OpenRouter connected · saved on this Mac':'No API key connected. Local processing is ready.';if(h.key_set){$('#transcription').value='openrouter';$('#selection').value='openrouter';$('#local-model-label').hidden=true}fillGhl(h.ghl);fillBrand(h.brand,h.links);return h}
function showView(name){
 $('#welcome').hidden=name!=='welcome';$('#project').hidden=name!=='project';$('#calendar').hidden=name!=='calendar';$('#saved').hidden=name!=='saved';
 $('#home').classList.toggle('active',name==='welcome');$('#calendar-nav').classList.toggle('active',name==='calendar');$('#saved-nav').classList.toggle('active',name==='saved');
 if(name==='calendar'){$('#crumb').textContent='Calendar';renderCalendar().catch(e=>toast(e.message,true))}
 if(name==='saved'){$('#crumb').textContent='Saved';renderSaved().catch(e=>toast(e.message,true))}
}
function localStamp(d){const p=n=>String(n).padStart(2,'0');return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`}
function dayIso(day,time='09:00'){const [h,m]=(time||'09:00').split(':');const d=new Date(day.getFullYear(),day.getMonth(),day.getDate(),Number(h)||0,Number(m)||0);if(d.getTime()<Date.now()+5*60*1000)d.setTime(Date.now()+5*60*1000);return d.toISOString()}
function clipCaption(c){const spoken=(project.transcript?.words||[]).filter(w=>w.start>=c.start&&w.start<c.end).map(w=>w.word).join(' ').replace(/\s+/g,' ').trim();const text=spoken.length>1800?spoken.slice(0,1797)+'…':spoken;return [c.title,text].filter(Boolean).join('\n\n')||'New clip'}
async function loadAccounts(){if(!ghlInfo.connected){ghlAccounts=[];return []}const data=await api('/ghl/accounts');ghlAccounts=data.accounts||[];return ghlAccounts}
async function loadUsers(){if(!ghlInfo.connected){ghlUsers=[];return []}const data=await api('/ghl/users');ghlUsers=data.users||[];if(!ghlInfo.user&&ghlUsers[0])ghlInfo.user=ghlUsers[0].id;fillUserSelect('#ghl-user',ghlInfo.user);fillUserSelect('#schedule-user',ghlInfo.user);fillUserSelect('#quick-user',ghlInfo.user);return ghlUsers}
function accountBoxes(id,selectedIds){const pick=new Set(selectedIds||ghlInfo.accounts||[]);$(id).innerHTML=ghlAccounts.length?ghlAccounts.map(a=>`<label><input type="checkbox" value="${esc(a.id)}" ${pick.has(a.id)?'checked':''}><span>${esc(a.name||a.platform||'Account')} · ${esc(a.platform||'')}</span></label>`).join(''):'<p class="tiny muted">No social accounts yet. Connect them in GHL Social Planner, then Test connection in Settings.</p>'}
function checkedAccounts(id){return $$(`${id} input:checked`).map(x=>x.value)}
async function library(){
 const list=await api('/projects');$('#project-count').textContent=list.length;$('#library-count').textContent=`${list.length} ${list.length===1?'project':'projects'}`;
 $('#projects').innerHTML=list.slice(0,10).map(p=>`<button class="project-link" data-project="${p.id}"><span>▧</span><span>${esc(p.title)}</span></button>`).join('');
 $('#library').innerHTML=list.length?list.map(p=>`<button class="library-card" data-project="${p.id}">${p.state==='ready'?`<img src="${mediaUrl(p.id,'poster.jpg')}" alt="Video thumbnail">`:'<div class="empty">Preparing video…</div>'}<div><b>${esc(p.title)}</b><small>${p.meta?clock(p.meta.duration)+' · ':''}${p.clips.length} clips · ${new Date(p.created*1000).toLocaleDateString()}</small></div></button>`).join(''):'<div class="empty"><div class="symbol">▧</div>Your next great clip starts here.<br>Import a video to create your first project.</div>';
 $$('[data-project]').forEach(b=>b.onclick=safe(()=>loadProject(b.dataset.project)));
}
async function loadProject(id){
 project=await api('/projects/'+id);selected=null;showView('project');$('#crumb').textContent='Video project';$('#project-title').textContent=project.title;$('#project-meta').textContent=project.meta?`${clock(project.meta.duration)} source · ${project.meta.width} × ${project.meta.height} · Saved locally`:'Preparing your video…';
 $('#source-label').textContent=project.source?'IMPORTED FROM A VIDEO LINK':'UPLOADED VIDEO';$('#download-source').href=asset('source.mp4',true);$('#download-source').hidden=project.state!=='ready';$('#generator').hidden=false;$('#editor').hidden=true;
 if(project.state==='ready')sourcePreview();else{$('#player').removeAttribute('src');$('#player').load()}
 renderClips();renderTranscript();drawSpeech();drawRange();$('#generate').disabled=project.state!=='ready';$('#manual').disabled=project.state!=='ready';history.replaceState(null,'',location.pathname+'?project='+id);
}
function sourcePreview(time){showingExport=false;$('#player').src=asset('source.mp4');$('#player').poster=asset('poster.jpg');$('#preview-label').textContent='Source preview';$('#video-stage').classList.remove('export');$('#preview-caption').hidden=false;$('#player').onloadedmetadata=()=>{if(time!==undefined)$('#player').currentTime=time};}
function drawSpeech(){const words=project?.transcript?.words||[];const duration=project?.meta?.duration||1;const bins=Array(120).fill(0);words.forEach(w=>bins[Math.min(119,Math.floor(w.start/duration*120))]++);const max=Math.max(...bins,1);$('#speech-map').innerHTML=bins.map(n=>`<i style="height:${2+n/max*16}px"></i>`).join('');}
function renderClips(){
 $('#clip-count').textContent=project.clips.length;$('#bundle').hidden=!project.clips.some(c=>c.export&&!c.dirty);$('#bundle').href=ENGINE+'/api/projects/'+project.id+'/bundle';
 $('#clips').innerHTML=project.clips.length?project.clips.map((c,i)=>`<article class="clip-card ${selected?.id===c.id?'selected':''}" data-clip="${c.id}"><div class="clip-image" data-preview="${c.id}"><img src="${asset(c.export?'exports/'+c.export.id+'/poster.jpg':'poster.jpg')}" alt="${esc(c.title)}"><span class="clip-badge">${c.selection==='manual'?'MANUAL':c.selection==='openrouter'?'✦ AI '+c.score:'LOCAL '+c.score}</span>${c.saved?`<span class="saved-pill">${c.ghl?.url?'SAVED · GHL':'SAVED'}</span>`:''}<span class="play">▶</span><span class="clip-duration">${clock(c.export&&!c.dirty?c.export.duration:c.end-c.start)}</span></div><div class="clip-copy"><input class="clip-pick" type="checkbox" data-pick="${c.id}" ${picked.has(c.id)?'checked':''} aria-label="Select ${esc(c.title)}" ${c.export&&!c.dirty?'':'disabled'}><h3>${esc(c.title)}</h3><p>${clock(c.start)} — ${clock(c.end)} · ${c.aspect==='vertical'?'9:16':c.aspect==='square'?'1:1':'16:9'}</p><p>${c.saved?'Saved':'Ready'}${c.dirty?' · render to update':c.export?' · MP4 ready':''}${c.ghl?.posts?.length?' · Scheduled':''}</p><div class="clip-actions"><button class="text-button" data-edit="${c.id}">Edit clip ↗</button>${c.export&&!c.dirty?`<a href="${asset('exports/'+c.export.id+'/clip.mp4',true)}" download>↓ MP4</a><button class="text-button" data-save="${c.id}">${c.saved?'Saved':'Save'}</button><button class="text-button" data-schedule="${c.id}">Schedule</button>`:`<button class="text-button" data-render="${c.id}">Render</button>`}</div></div></article>`).join(''):'<div class="empty"><div class="symbol">✦</div>Your best moments are in there.<br>Choose your settings and generate clips, or add a manual cut.</div>';
 $$('[data-edit]').forEach(b=>b.onclick=()=>editClip(b.dataset.edit));$$('[data-preview]').forEach(b=>b.onclick=()=>previewClip(b.dataset.preview));$$('[data-render]').forEach(b=>b.onclick=safe(async()=>track(await api(`/projects/${project.id}/clips/${b.dataset.render}/export`,{}))));
 $$('[data-pick]').forEach(b=>b.onclick=e=>{e.stopPropagation();if(b.checked)picked.add(b.dataset.pick);else picked.delete(b.dataset.pick)});
 $$('[data-schedule]').forEach(b=>b.onclick=safe(e=>{e.stopPropagation();return openSchedule(b.dataset.schedule)}));
 $$('[data-save]').forEach(b=>b.onclick=safe(async e=>{e.stopPropagation();if(project.clips.find(c=>c.id===b.dataset.save)?.saved)return;track(await api(`/projects/${project.id}/clips/${b.dataset.save}/save`,{}))}));
}
function previewClip(id){const c=project.clips.find(x=>x.id===id);if(c.export&&!c.dirty){showingExport=true;$('#player').src=asset('exports/'+c.export.id+'/clip.mp4');$('#player').poster=asset('exports/'+c.export.id+'/poster.jpg');$('#preview-label').textContent='Rendered clip · '+c.title;$('#video-stage').classList.add('export');$('#preview-caption').hidden=true;$('#player').onloadedmetadata=()=>$('#player').play().catch(()=>{});}else{sourcePreview(c.start);$('#preview-label').textContent='Source selection · '+c.title;$('#player').onloadedmetadata=()=>{$('#player').currentTime=c.start;$('#player').play().catch(()=>{})}}}
function editClip(id){selected=structuredClone(project.clips.find(c=>c.id===id));$('#generator').hidden=true;$('#editor').hidden=false;$('#edit-title').value=selected.title;$('#edit-start').value=selected.start;$('#edit-end').value=selected.end;$('#aspect').value=selected.aspect;$('#framing').value=selected.framing;$('#focus').value=selected.focus_x;$('#zoom').value=1;$('#auto-zoom').checked=selected.auto_zoom;$('#remove-silence').checked=selected.remove_silence;$('#captions').checked=selected.captions;$('#caption-style').value=selected.caption_style||brand.style;$('#edit-font').value=selected.caption_font||brand.font;$('#edit-color').value=selected.caption_color||brand.color;$('#edit-highlight').value=selected.caption_highlight||brand.highlight;$('#resolution').value=selected.resolution;updateSliders();keyframes();sourcePreview(selected.start);renderClips();}
function clipBody(){return {...selected,title:$('#edit-title').value,start:Number($('#edit-start').value),end:Number($('#edit-end').value),aspect:$('#aspect').value,framing:$('#framing').value,focus_x:Number($('#focus').value),auto_zoom:$('#auto-zoom').checked,remove_silence:$('#remove-silence').checked,captions:$('#captions').checked,caption_style:$('#caption-style').value,caption_font:$('#edit-font').value,caption_color:$('#edit-color').value.toUpperCase(),caption_highlight:$('#edit-highlight').value.toUpperCase(),resolution:Number($('#resolution').value)}}
async function saveClip(){if(!selected)return;const c=await api(`/projects/${project.id}/clips/${selected.id}`,clipBody(),'PUT');project.clips[project.clips.findIndex(x=>x.id===c.id)]=c;selected=structuredClone(c);renderClips();return c;}
function keyframes(){$('#keyframes').innerHTML=(selected.keyframes||[]).sort((a,b)=>a.time-b.time).map((p,i)=>`<div class="keyframe"><span>◇ ${p.time.toFixed(2)}s</span><span>x ${Math.round(p.x*100)}% · ${p.zoom.toFixed(2)}×</span><button class="text-button" data-remove-key="${i}" aria-label="Remove keyframe ${i+1}">×</button></div>`).join('');$$('[data-remove-key]').forEach(b=>b.onclick=()=>{selected.keyframes.splice(Number(b.dataset.removeKey),1);keyframes()})}
function updateSliders(){$('#focus-value').textContent=Math.round(Number($('#focus').value)*100)+'%';$('#zoom-value').textContent=Number($('#zoom').value).toFixed(2)+'×'}
$('#focus').oninput=updateSliders;$('#zoom').oninput=updateSliders;
$('#add-keyframe').onclick=safe(()=>{if(showingExport)throw Error('Switch to source preview to add a keyframe.');const t=Number(($('#player').currentTime-Number($('#edit-start').value)).toFixed(2));if(t<0||t>Number($('#edit-end').value)-Number($('#edit-start').value))throw Error('Move the playhead inside this clip first.');const p={time:t,x:Number($('#focus').value),y:.5,zoom:Number($('#zoom').value)};selected.keyframes=selected.keyframes.filter(k=>Math.abs(k.time-t)>.03);selected.keyframes.push(p);keyframes();toast('Keyframe added. Save & render to preview the camera move.')});
$('#save-clip').onclick=safe(async()=>{await saveClip();toast('Edit saved.')});$('#render-clip').onclick=safe(async()=>{const c=await saveClip();track(await api(`/projects/${project.id}/clips/${c.id}/export`,{}))});
$('#set-start').onclick=()=>{if(!showingExport)$('#edit-start').value=$('#player').currentTime.toFixed(2)};$('#set-end').onclick=()=>{if(!showingExport)$('#edit-end').value=$('#player').currentTime.toFixed(2)};
$('#close-editor').onclick=()=>{selected=null;$('#generator').hidden=false;$('#editor').hidden=true;renderClips()};
$('#show-source').onclick=()=>sourcePreview(selected?.start||0);
function renderTranscript(){
 const words=project.transcript?.words||[];let last=-1,html='';
 words.forEach((w,i)=>{if(last<0||w.start-last>12){if(last>=0)html+='</div></div>';last=w.start;html+=`<div class="transcript-row"><span class="transcript-time" data-seek="${w.start}">${clock(w.start)}</span><div>`}html+=`<span class="word" role="button" tabindex="0" data-word="${i}" data-seek="${w.start}">${esc(w.word)}</span> `});if(words.length)html+='</div></div>';
 $('#transcript').innerHTML=html||'<p class="muted">Your timestamped transcript will appear here after processing.</p>';$('#transcript-info').textContent=words.length?`${words.length.toLocaleString()} words · ${project.transcript.engine==='openrouter'?'OpenRouter':'Local Whisper'} · word timestamps · click to seek, Edit words to correct captions`:'Run Generate clips to create a transcript.';$('#more-clips').hidden=!words.length;$('#edit-transcript').hidden=!words.length||editingWords;
 $$('[data-seek]').forEach(b=>{b.onclick=()=>{if(editingWords)return;const t=Number(b.dataset.seek);if(showingExport)sourcePreview(t);else $('#player').currentTime=t};b.onkeydown=e=>{if(e.key==='Enter')b.click()}});
}
$('#transcript-search').oninput=()=>{const query=$('#transcript-search').value.toLowerCase();$$('.word').forEach(w=>w.classList.toggle('match',!!query&&w.textContent.toLowerCase().includes(query)))};
$('#edit-transcript').onclick=()=>{editingWords=true;$$('.word').forEach(w=>w.contentEditable='true');$('#save-transcript').hidden=false;$('#edit-transcript').hidden=true;toast('Edit individual words, then save. Word timestamps stay aligned.')};
$('#save-transcript').onclick=safe(async()=>{const words=project.transcript.words.map((w,i)=>({...w,word:$(`[data-word="${i}"]`).textContent.trim()}));await api(`/projects/${project.id}/transcript`,{words},'PUT');project=await api('/projects/'+project.id);editingWords=false;$('#save-transcript').hidden=true;$('#edit-transcript').hidden=false;renderTranscript();renderClips();toast('Transcript saved. Re-render clips to update captions.')});
$$('[data-tab]').forEach(b=>b.onclick=()=>{$$('[data-tab]').forEach(x=>x.classList.toggle('selected',x===b));$('#clips-panel').hidden=b.dataset.tab!=='clips';$('#transcript-panel').hidden=b.dataset.tab!=='transcript'});
$('#player').ontimeupdate=()=>{const v=$('#player');$('#play-time').textContent=clock(v.currentTime);$('#total-time').textContent=clock(v.duration);$('#scrubber').max=v.duration||100;$('#scrubber').value=v.currentTime;
 if(!showingExport&&project?.transcript){const words=project.transcript.words;const index=words.findIndex(w=>v.currentTime>=w.start&&v.currentTime<w.end);const start=Math.floor(index/4)*4;$('#preview-caption').innerHTML=index>=0?words.slice(start,start+4).map((w,i)=>i+start===index?`<mark>${esc(w.word)}</mark>`:esc(w.word)).join(' '):'';$$('.word.current').forEach(w=>w.classList.remove('current'));if(index>=0)$(`[data-word="${index}"]`)?.classList.add('current')}else $('#preview-caption').innerHTML='';
 if(!showingExport&&selected&&v.currentTime>=Number($('#edit-end').value)&&!v.paused)v.pause();};
$('#scrubber').oninput=()=>$('#player').currentTime=Number($('#scrubber').value);
function timeAt(el,x){const r=el.getBoundingClientRect();const d=project?.meta?.duration||0;return Math.max(0,Math.min(d,((x-r.left)/Math.max(r.width,1))*d))}
function drawRange(){const mark=$('#range-mark');if(!mark)return;if(!rangeSel){mark.hidden=true;$('#timeline-note').textContent='Drag the bar under the video to pick a section.';return}const d=project?.meta?.duration||1;const a=Math.min(rangeSel.start,rangeSel.end),b=Math.max(rangeSel.start,rangeSel.end);mark.hidden=false;mark.style.left=(a/d*100)+'%';mark.style.width=(Math.max(b-a,0)/d*100)+'%';$('#timeline-note').textContent=`${clock(a)}–${clock(b)} selected · Generate or Manual clip uses this`}
$('#speech-wrap').onpointerdown=e=>{if(showingExport||!project?.meta)return;rangeDrag=timeAt($('#speech-wrap'),e.clientX);rangeSel={start:rangeDrag,end:rangeDrag};$('#speech-wrap').setPointerCapture(e.pointerId)};
$('#speech-wrap').onpointermove=e=>{if(rangeDrag==null)return;rangeSel={start:rangeDrag,end:timeAt($('#speech-wrap'),e.clientX)};drawRange()};
$('#speech-wrap').onpointerup=e=>{if(rangeDrag==null)return;const end=timeAt($('#speech-wrap'),e.clientX);const a=Math.min(rangeDrag,end),b=Math.max(rangeDrag,end);rangeDrag=null;if(b-a<1){rangeSel=null;drawRange();return}rangeSel={start:a,end:b};if(!showingExport)$('#player').currentTime=a;drawRange()};
$('#speech-wrap').ondblclick=()=>{rangeSel=null;drawRange()};
async function imported(result){await library();await loadProject(result.project.id);track(result.job)}
$('#import-form').onsubmit=safe(async e=>{e.preventDefault();$('#import-button').disabled=true;try{await imported(await api('/import/url',{url:$('#source-url').value.trim()}))}finally{$('#import-button').disabled=false}});
async function upload(file){if(!file)return;if(file.size>8*1024**3)throw Error('Maximum upload size is 8 GB.');const form=new FormData();form.append('file',file);toast('Uploading video to your local service…');await imported(await api('/import/upload',form));$('#file').value=''}
$('#file').onchange=safe(e=>upload(e.target.files[0]));$('#dropzone').ondragover=e=>{e.preventDefault();$('#dropzone').classList.add('drag')};$('#dropzone').ondragleave=()=>$('#dropzone').classList.remove('drag');$('#dropzone').ondrop=safe(e=>{e.preventDefault();$('#dropzone').classList.remove('drag');return upload(e.dataTransfer.files[0])});
$('#count-minus').onclick=()=>$('#count').textContent=count=Math.max(1,count-1);$('#count-plus').onclick=()=>$('#count').textContent=count=Math.min(12,count+1);
$('#transcription').onchange=()=>$('#local-model-label').hidden=$('#transcription').value!=='local';
function generateClips(){const body={count,length:Number($('#length').value),transcription:$('#transcription').value,selection:$('#selection').value,local_model:$('#local-model').value,brief:$('#brief').value,auto_export:$('#auto-export').checked,...brandFields('gen')};if(rangeSel){const a=Math.min(rangeSel.start,rangeSel.end),b=Math.max(rangeSel.start,rangeSel.end);if(b-a>=1){body.window_start=a;body.window_end=b}}return api(`/projects/${project.id}/analyze`,body)}
$('#generate').onclick=safe(async()=>track(await generateClips()));
$('#more-clips').onclick=safe(async()=>{$$('[data-tab]').find(b=>b.dataset.tab==='clips')?.click();track(await generateClips())});
$('#manual').onclick=safe(async()=>{const duration=project.meta.duration;let start,end;if(rangeSel&&Math.abs(rangeSel.end-rangeSel.start)>=1){start=Math.min(rangeSel.start,rangeSel.end);end=Math.min(duration,Math.max(rangeSel.start,rangeSel.end))}else{start=Math.min(showingExport?0:$('#player').currentTime,Math.max(0,duration-1));end=Math.min(start+45,duration)}const c=await api(`/projects/${project.id}/clips`,{start,end,title:'New manual clip',...brandFields('gen')});project.clips.push(c);editClip(c.id)});
$('#export-all').onclick=safe(async()=>track(await api(`/projects/${project.id}/export`,{})));
function track(job){currentJob=job;$('#job-dock').hidden=false;updateJob(job)}
function updateJob(j){$('#job-message').textContent=j.message;$('#job-progress').style.width=Math.max(2,j.progress*100)+'%';$('#cancel-job').disabled=['done','error','cancelled'].includes(j.state)}
$('#cancel-job').onclick=safe(async()=>{if(currentJob)await api('/jobs/'+currentJob.id+'/cancel',{});toast('Cancelling current operation…')});
async function poll(){if(polling)return;polling=true;try{const jobs=await api('/jobs');const active=jobs.find(j=>j.project===project?.id&&['queued','running'].includes(j.state))||jobs.find(j=>['queued','running'].includes(j.state));if(active)track(active);else if(currentJob){const ended=jobs.find(j=>j.id===currentJob.id);if(ended&&!seenJobs.has(ended.id)){seenJobs.add(ended.id);$('#job-dock').hidden=true;currentJob=null;if(ended.state==='error')toast(ended.message,true);else if(ended.state==='cancelled')toast('Operation cancelled. Completed work is saved.');else toast('Ready. Your project has been saved.');if(project?.id===ended.project){const id=selected?.id;await loadProject(project.id);if(id&&project.clips.some(c=>c.id===id))editClip(id)}await library();await renderSaved().catch(()=>{})}}const busy=project?.state!=='ready'||!!jobs.find(j=>j.project===project?.id&&['queued','running'].includes(j.state));$('#generate').disabled=busy;if($('#more-clips'))$('#more-clips').disabled=busy;$('#connection').textContent='Automatic engine connected';$('#connection').classList.remove('offline')}catch{$('#connection').textContent='Restarting private engine…';$('#connection').classList.add('offline');startEngine().catch(()=>{$('#connection').textContent='Engine unavailable · run installer'})}finally{polling=false}}
function home(){project=null;selected=null;showView('welcome');$('#crumb').textContent='Video library';$('#player').pause();history.replaceState(null,'',location.pathname);library().catch(e=>toast(e.message,true))}
$('#home').onclick=home;$('#new').onclick=()=>{home();$('#source-url').focus()};
$('#calendar-nav').onclick=safe(async()=>{await health();showView('calendar')});
$('#saved-nav').onclick=safe(()=>showView('saved'));
async function renderSaved(){
 const data=await api('/saved');const clips=data.clips||[];$('#saved-count').textContent=clips.length;
 $('#saved-grid').innerHTML=clips.length?clips.map(c=>`<button class="library-card" data-open-saved="${c.project_id}"><img src="${mediaUrl(c.project_id,c.export_id?`exports/${c.export_id}/poster.jpg`:'poster.jpg')}" alt="${esc(c.title)}"><div><b>${esc(c.title)}</b><small>${esc(c.project)} · ${c.ghl?'Saved in GHL':'Saved locally'}</small></div></button>`).join(''):'<div class="empty"><div class="symbol">★</div>Save a rendered clip to keep it here and upload it to GoHighLevel media storage.</div>';
 $$('[data-open-saved]').forEach(b=>b.onclick=safe(()=>loadProject(b.dataset.openSaved)));
}
function monthLabel(d){return d.toLocaleString(undefined,{month:'long',year:'numeric'})}
function postWhen(p){return new Date(p.scheduleDate||p.schedule_date||p.createdAt||p.updatedAt||Date.now())}
function renderMiniCal(){
 $('#mini-month').textContent=monthLabel(miniCursor);
 const start=new Date(miniCursor.getFullYear(),miniCursor.getMonth(),1);const pad=start.getDay();const days=new Date(miniCursor.getFullYear(),miniCursor.getMonth()+1,0).getDate();
 let html='SMTWTFS'.split('').map(d=>`<span class="dow">${d}</span>`).join('');
 for(let i=0;i<pad;i++)html+='<span></span>';
 for(let n=1;n<=days;n++){const day=new Date(miniCursor.getFullYear(),miniCursor.getMonth(),n);const on=pickedDay.toDateString()===day.toDateString();html+=`<button type="button" class="${on?'picked':''}" data-mini="${day.toISOString()}">${n}</button>`}
 $('#mini-cal').innerHTML=html;$$('[data-mini]').forEach(b=>b.onclick=()=>{pickedDay=new Date(b.dataset.mini);renderMiniCal()});
}
function fillPicks(id,items,target,picked){
 const list=items||[];
 $(id).innerHTML=list.map((p,i)=>`<button type="button" class="copy-opt ${i===picked?'on':''}" data-i="${i}"><b>${esc(p.label||'Option')}</b><span>${esc(p.text)}</span></button>`).join('')+`<button type="button" class="copy-opt" data-own="1"><b>Write my own</b><span>Edit the box below.</span></button>`;
 $$(`${id} .copy-opt`).forEach(b=>b.onclick=()=>{$$(`${id} .copy-opt`).forEach(x=>x.classList.toggle('on',x===b));if(!b.dataset.own)$(target).value=list[Number(b.dataset.i)]?.text||'';$(target).focus()});
 if(list[picked])$(target).value=list[picked].text;
}
function useSocial(social){
 const posts=social?.posts||[];const comments=social?.comments||[];
 fillPicks('#post-picks',posts,'#schedule-summary',0);
 fillPicks('#comment-picks',comments,'#schedule-follow',0);
 if(!posts.length)$('#schedule-summary').value=clipCaption(scheduleClip);
}
async function loadSocial(force){
 if(!scheduleClip)return;
 if(!force&&scheduleClip.social?.posts?.length){useSocial(scheduleClip.social);return scheduleClip.social}
 $('#post-picks').innerHTML='<p class="tiny muted">Writing 3 captions…</p>';$('#comment-picks').innerHTML='<p class="tiny muted">Writing first comments…</p>';
 const social=await api(`/projects/${project.id}/clips/${scheduleClip.id}/copy`,{});
 scheduleClip.social=social;const row=project.clips.find(c=>c.id===scheduleClip.id);if(row)row.social=social;
 useSocial(social);return social;
}
async function openSchedule(id){
 if(!ghlInfo.connected){$('#settings').showModal();throw Error('Save your GoHighLevel location and token in Settings first.')}
 const c=project.clips.find(x=>x.id===id);if(!c?.export||c.dirty)throw Error('Render this clip first, then schedule it.');
 scheduleClip=c;pickedDay=new Date();miniCursor=new Date();$('#schedule-title').textContent=c.title;$('#schedule-type').value=c.aspect==='vertical'?'reel':'post';
 await loadAccounts();await loadUsers();accountBoxes('#schedule-accounts');renderMiniCal();
 const soon=new Date(Date.now()+10*60*1000);$('#schedule-time').value=soon.toTimeString().slice(0,5);
 $('#schedule-dialog').showModal();
 await loadSocial(false);
}
async function submitSchedule(status,now=false){
 if(!scheduleClip)return;
 const account_ids=checkedAccounts('#schedule-accounts');if(!account_ids.length)throw Error('Choose at least one social account.');
 const user_id=$('#schedule-user').value;if(!user_id)throw Error('Pick who is posting.');
 track(await api(`/projects/${project.id}/clips/${scheduleClip.id}/publish`,{account_ids,user_id,summary:$('#schedule-summary').value,follow_up:$('#schedule-follow').value,schedule_date:now?'':dayIso(pickedDay,$('#schedule-time').value),type:$('#schedule-type').value,status:now?'published':'scheduled'}));
 $('#schedule-dialog').close();showView('calendar');
}
function postIds(p){return p.accountIds||p.accountids||(p.accountId?[p.accountId]:[])}
function postMedia(p){const m=p.media||[];return (m[0]&&(m[0].url||m[0]))||p.mediaUrl||''}
function sameBundle(a,b){if(Math.abs(postWhen(a)-postWhen(b))>3*60*1000)return false;const sa=(a.summary||'').split('\n')[0].slice(0,50).toLowerCase();const sb=(b.summary||'').split('\n')[0].slice(0,50).toLowerCase();if(sa&&sb&&sa===sb)return true;const ma=postMedia(a),mb=postMedia(b);return !!(ma&&mb&&ma===mb)}
function clusterPosts(items){const groups=[];for(const p of items.slice().sort((a,b)=>postWhen(a)-postWhen(b))){const g=groups.find(x=>sameBundle(x[0],p));if(g)g.push(p);else groups.push([p])}return groups}
async function renderCalendar(){
 $('#cal-month').textContent=monthLabel(calCursor);
 const start=new Date(calCursor.getFullYear(),calCursor.getMonth(),1);const pad=start.getDay();
 const last=new Date(calCursor.getFullYear(),calCursor.getMonth()+1,0);
 const from=new Date(start);from.setHours(0,0,0,0);const to=new Date(last);to.setHours(23,59,59,0);
 if(ghlInfo.connected&&!ghlAccounts.length)await loadAccounts().catch(()=>{});
 let posts=[];if(ghlInfo.connected){try{posts=(await api(`/ghl/posts?from_date=${encodeURIComponent(from.toISOString())}&to_date=${encodeURIComponent(to.toISOString())}`)).posts||[]}catch(e){$('#calendar-status').textContent=e.message}}
 calendarPosts=posts;
 const byDay={};posts.forEach(p=>{const key=postWhen(p).toDateString();(byDay[key]=byDay[key]||[]).push(p)});
 const today=new Date().toDateString();let html='SMTWTFS'.split('').map(d=>`<div class="cal-dow">${d}</div>`).join('');
 for(let i=0;i<pad;i++)html+='<div class="cal-pad"></div>';
 for(let n=1;n<=last.getDate();n++){const day=new Date(calCursor.getFullYear(),calCursor.getMonth(),n);const groups=clusterPosts(byDay[day.toDateString()]||[]);
  html+=`<div class="cal-day${day.toDateString()===today?' today':''}" data-drop="${day.toISOString()}"><b>${n}</b>${groups.map(g=>{const p=g[0];const ids=[...new Set(g.flatMap(postIds))];const plats=g.map(x=>x.platform||x.type).filter(Boolean);const when=postWhen(p);return `<button class="cal-post" draggable="true" data-post="${esc(p._id||p.id)}" data-ids="${esc(g.map(x=>x._id||x.id).join(','))}" data-when="${esc(when.toISOString())}"><span class="cal-row"><span class="cal-time">${when.toLocaleTimeString([], {hour:'numeric',minute:'2-digit'})}</span><span class="cal-icons">${socIcons(ids,plats)}</span></span><span class="cal-title">${esc((p.summary||'Post').split('\n')[0].slice(0,42))}</span></button>`}).join('')}</div>`}
 $('#calendar-grid').innerHTML=html;
 $$('.cal-post').forEach(b=>{b.ondragstart=e=>{e.dataTransfer.setData('text/plain',JSON.stringify({id:b.dataset.post,ids:(b.dataset.ids||'').split(',').filter(Boolean),when:b.dataset.when}))};b.onclick=safe(()=>openPostDetail(b.dataset.post,(b.dataset.ids||'').split(',').filter(Boolean)))});
 $$('[data-drop]').forEach(cell=>{cell.ondragover=e=>{e.preventDefault();cell.classList.add('drop')};cell.ondragleave=()=>cell.classList.remove('drop');cell.ondrop=safe(async e=>{e.preventDefault();cell.classList.remove('drop');const payload=JSON.parse(e.dataTransfer.getData('text/plain')||'{}');const ids=payload.ids?.length?payload.ids:[payload.id].filter(Boolean);if(!ids.length)return;const old=new Date(payload.when);const dest=new Date(cell.dataset.drop);dest.setHours(old.getHours(),old.getMinutes(),0,0);for(const id of ids)await api(`/ghl/posts/${id}`,{schedule_date:dest.toISOString()},'PUT');toast(ids.length>1?`Moved ${ids.length} platform posts.`:'Post moved.');await renderCalendar()})});
}
async function openQuick(){
 if(!project)throw Error('Open a project and select rendered clips first.');
 const ids=[...picked].filter(id=>project.clips.some(c=>c.id===id&&c.export&&!c.dirty));
 if(!ids.length)throw Error('Check the clips you want, then click Quick schedule. Render them first if needed.');
 if(!ghlInfo.connected){$('#settings').showModal();throw Error('Save your GoHighLevel location and token in Settings first.')}
 $('#quick-count').textContent=`${ids.length} clip${ids.length===1?'':'s'} will be spaced from the start time. Captions fill in from each title and transcript.`;
 const start=new Date();start.setMinutes(0,0,0);start.setHours(start.getHours()+1);$('#quick-start').value=localStamp(start);
 await loadAccounts();await loadUsers();accountBoxes('#quick-accounts');$('#quick-dialog').showModal();
}
$('#cal-prev').onclick=safe(async()=>{calCursor=new Date(calCursor.getFullYear(),calCursor.getMonth()-1,1);await renderCalendar()});
$('#cal-next').onclick=safe(async()=>{calCursor=new Date(calCursor.getFullYear(),calCursor.getMonth()+1,1);await renderCalendar()});
$('#mini-prev').onclick=()=>{miniCursor=new Date(miniCursor.getFullYear(),miniCursor.getMonth()-1,1);renderMiniCal()};
$('#mini-next').onclick=()=>{miniCursor=new Date(miniCursor.getFullYear(),miniCursor.getMonth()+1,1);renderMiniCal()};
function accountName(id){const a=ghlAccounts.find(x=>x.id===id);return a?`${a.name||a.platform} · ${a.platform||''}`:id}
function openPostDetail(id,groupIds){
 const listed=calendarPosts.find(p=>(p._id||p.id)===id)||{};
 return (async()=>{
  let post=listed;
  try{post={...listed,...await api('/ghl/posts/'+id)}}catch{}
  activePost=post;
  if(!ghlAccounts.length&&ghlInfo.connected)await loadAccounts().catch(()=>{});
  const when=postWhen(post);
  const group=(groupIds||[id]).map(gid=>calendarPosts.find(p=>(p._id||p.id)===gid)||(gid===id?post:null)).filter(Boolean);
  const ids=[...new Set(group.flatMap(postIds).concat(post.accountIds||post.accountids||[]))];
  const plats=group.map(p=>p.platform||p.type).filter(Boolean);
  const media=(post.media||[]).map(m=>m.url||m).filter(Boolean);
  $('#post-detail-status').textContent=(post.status||'scheduled').replaceAll('_',' ');
  $('#post-detail-title').innerHTML=`${esc((post.summary||'Post').split('\n')[0].slice(0,80)||'Post')} <span class="cal-icons">${socIcons(ids,plats)}</span>`;
  $('#post-detail-meta').textContent=`${when.toLocaleString()} · ${post.type||'post'}${posterName()?' · '+posterName():''}`;
  $('#post-detail-summary').value=post.summary||'';
  $('#post-detail-follow').value=post.followUpComment||post.follow_up||'';
  $('#post-detail-extra').textContent=[ids.length?`Accounts: ${ids.map(accountName).join(', ')}`:'',media.length?`Media: ${media.length} file${media.length===1?'':'s'}`:'',group.length>1?`${group.length} platform posts grouped`:'',post.error||post.failedReason||''].filter(Boolean).join('\n');
  $('#post-detail-when').value=localStamp(when);
  $('#post-dialog').showModal();
 })();
}
$('#schedule-save').onclick=safe(()=>submitSchedule('scheduled'));
$('#post-now').onclick=safe(()=>submitSchedule('scheduled',true));
$('#post-detail-save').onclick=safe(async()=>{if(!activePost)return;const when=new Date($('#post-detail-when').value);if(Number.isNaN(+when))throw Error('Pick a valid date and time.');await api(`/ghl/posts/${activePost._id||activePost.id}`,{schedule_date:when.toISOString()},'PUT');$('#post-dialog').close();toast('Post updated.');await renderCalendar()});
$('#post-detail-delete').onclick=safe(async()=>{if(!activePost||!confirm('Delete this scheduled post?'))return;await api(`/ghl/posts/${activePost._id||activePost.id}`,{},'DELETE');$('#post-dialog').close();toast('Post deleted.');await renderCalendar()});
$('#quick-from-clips').onclick=safe(openQuick);$('#quick-schedule-open').onclick=safe(openQuick);
$('#quick-save').onclick=safe(async()=>{const account_ids=checkedAccounts('#quick-accounts');if(!account_ids.length)throw Error('Choose at least one social account.');const user_id=$('#quick-user').value;if(!user_id)throw Error('Pick who is posting.');const clip_ids=[...picked].filter(id=>project.clips.some(c=>c.id===id&&c.export&&!c.dirty));track(await api(`/projects/${project.id}/publish`,{clip_ids,account_ids,user_id,follow_up:$('#quick-follow').value,start:new Date($('#quick-start').value).toISOString(),interval_hours:Number($('#quick-interval').value),type:$('#quick-type').value}));$('#quick-dialog').close();showView('calendar')});
function settingsBody(extra){const body={model:$('#ai-model').value,stt_model:$('#stt-model').value,ghl_location:$('#ghl-location').value.trim(),ghl_user:$('#ghl-user').value,caption_font:$('#set-font').value,caption_color:$('#set-color').value.toUpperCase(),caption_highlight:$('#set-highlight').value.toUpperCase(),caption_style:$('#set-caption-style').value,site_url:$('#set-site').value.trim(),course_url:$('#set-course').value.trim()};if($('#api-key').value)body.key=$('#api-key').value;if($('#ghl-token').value)body.ghl_token=$('#ghl-token').value.trim();return Object.assign(body,extra||{})}
$('#settings-open').onclick=safe(async()=>{await health();$('#settings').showModal();if(ghlInfo.connected)await loadUsers().catch(()=>{})});
$('#settings-save').onclick=safe(async()=>{const body=settingsBody();if(!body.ghl_location){body.ghl_token='';body.ghl_accounts=[]}const result=await api('/settings',body);$('#api-key').value='';$('#ghl-token').value='';fillGhl(result.ghl);fillBrand(result.brand,result.links);$('#settings').close();if(result.key_set){$('#transcription').value='openrouter';$('#selection').value='openrouter';$('#local-model-label').hidden=true}toast('Settings saved on this Mac.')});
$('#ghl-test').onclick=safe(async()=>{const result=await api('/settings',settingsBody());fillGhl(result.ghl);fillBrand(result.brand,result.links);const [accounts,staff]=await Promise.all([loadAccounts(),loadUsers()]);if(staff[0]&&!$('#ghl-user').value){$('#ghl-user').value=staff[0].id;await api('/settings',settingsBody({ghl_user:staff[0].id}))}toast(`Connected. ${accounts.length} account${accounts.length===1?'':'s'}, ${staff.length} staff. Pick who is posting.`)});
$('#rewrite-copy').onclick=safe(async()=>{if(!scheduleClip)return;$('#rewrite-copy').disabled=true;try{await loadSocial(true)}finally{$('#rewrite-copy').disabled=false}});
$('#disconnect').onclick=safe(async()=>{await api('/settings',{key:'',model:$('#ai-model').value,stt_model:$('#stt-model').value});$('#api-key').value='';$('#transcription').value='local';$('#selection').value='local';$('#local-model-label').hidden=false;await health();toast('OpenRouter disconnected.')});
$('#help').onclick=()=>$('#help-dialog').showModal();
async function startEngine(){
 if(!globalThis.chrome?.runtime?.sendMessage)return;
 const response=await chrome.runtime.sendMessage({type:'ensure-engine'});
 if(!response?.ok)throw Error(response?.error||'The ClipForge companion could not start. Run Install ClipForge once.');
}
async function init(){try{await startEngine();await health();await library();await renderSaved().catch(()=>{});const params=new URLSearchParams(location.search);if(params.get('source')){$('#source-url').value=params.get('source');toast('Video link is ready. Click Import video to download it.')}else if(params.get('project'))await loadProject(params.get('project'));await poll()}catch(e){toast('ClipForge could not start its private editing engine. '+e.message,true);$('#connection').textContent='Engine unavailable · run installer';$('#connection').classList.add('offline')}setInterval(poll,2000)}init();

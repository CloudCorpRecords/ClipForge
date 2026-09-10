"""Stateless video jobs; no accounts, cookies, settings or user data in the image."""
import gc,ipaddress,json,math,os,re,shutil,socket,tempfile,zipfile
from pathlib import Path as LocalPath
from typing import List,Optional
from urllib.parse import urlparse
os.environ['CLIPFORGE_FFMPEG']='/usr/bin/ffmpeg'
os.environ['OMP_NUM_THREADS']='1'
from cog import BasePredictor,Input,Path,BaseModel,Secret
import yt_dlp
import media,ai

class Output(BaseModel):
    manifest:Path
    source:Optional[Path]=None
    transcript:Optional[Path]=None
    poster:Optional[Path]=None
    clips:List[Path]=[]
    clip_posters:List[Path]=[]
    bundle:Optional[Path]=None

def public_url(url):
    p=urlparse(url)
    if p.scheme not in ('https','http') or not p.hostname or p.username or p.password:
        raise ValueError('Enter a public HTTPS video URL.')
    for address in socket.getaddrinfo(p.hostname,p.port or (443 if p.scheme=='https' else 80),type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(address[4][0]).is_global:raise ValueError('Private network URLs are not allowed.')
    return url

def download(url,destination):
    public_url(url)
    options=dict(ignoreconfig=True,noplaylist=True,cachedir=False,js_runtimes={'node':{}},
        format='bv*[vcodec^=avc1][height<=720]+ba[acodec^=mp4a]/b[vcodec^=avc1][height<=720]/b[height<=720]/best[height<=720]',
        outtmpl=str(destination/'download.%(ext)s'),merge_output_format='mp4',ffmpeg_location=media.FFMPEG,
        max_filesize=2*1024**3,match_filter=yt_dlp.utils.match_filter_func('duration <= 14400 & !is_live'),
        socket_timeout=30,retries=2,fragment_retries=2,quiet=False)
    try:
        with yt_dlp.YoutubeDL(options) as ydl: info=ydl.extract_info(url,download=True)
    except yt_dlp.utils.DownloadError as e:
        raise ValueError('The video host rejected this cloud download. Upload your original recording or use a direct video URL. '+str(e)[-400:]) from e
    paths=[p for p in destination.glob('download.*') if p.suffix in {'.mp4','.mkv','.webm','.mov'}]
    if not paths:raise ValueError('No video downloaded. Check duration/size limits or upload the original recording.')
    return paths[0],str((info or {}).get('title') or 'Your video')

def validate_edit(raw,duration):
    start=float(raw.get('start',0));end=float(raw.get('end',start+30))
    if not 0<=start<end<=duration+.1 or not 1<=end-start<=180:raise ValueError('Each clip must be 1–180 seconds and inside the source video.')
    aspect=raw.get('aspect','vertical');framing=raw.get('framing','fit')
    if aspect not in {'vertical','square','landscape'} or framing not in {'fit','face','center'}:raise ValueError('Invalid framing or canvas.')
    points=raw.get('keyframes') or []
    if not isinstance(points,list) or len(points)>50:raise ValueError('Use at most 50 keyframes.')
    clean=[]
    for point in points:
        t,x,y,z=(float(point.get(k,d)) for k,d in [('time',0),('x',.5),('y',.5),('zoom',1)])
        if not all(math.isfinite(v) for v in [t,x,y,z]) or not 0<=t<=end-start or not 0<=x<=1 or not 0<=y<=1 or not 1<=z<=2:raise ValueError('Keyframes need clip-relative time, x/y from 0–1 and zoom from 1–2.')
        clean.append(dict(time=t,x=x,y=y,zoom=z))
    if len({p['time'] for p in clean})!=len(clean):raise ValueError('Keyframe times must be unique.')
    return dict(start=start,end=end,title=str(raw.get('title') or 'Your clip')[:120],aspect=aspect,framing=framing,
        focus_x=max(0,min(1,float(raw.get('focus_x',.5)))),keyframes=sorted(clean,key=lambda p:p['time']),resolution=1080 if int(raw.get('resolution',1080))==1080 else 720,
        auto_zoom=bool(raw.get('auto_zoom',True)),remove_silence=bool(raw.get('remove_silence',True)),
        captions=bool(raw.get('captions',True)),caption_style='clean' if raw.get('caption_style')=='clean' else 'pop',caption_font=str(raw.get('caption_font','Arial'))[:80],
        caption_color=raw.get('caption_color','#FFFFFF') if re.fullmatch(r'#[0-9A-Fa-f]{6}',str(raw.get('caption_color','#FFFFFF'))) else '#FFFFFF',caption_highlight=raw.get('caption_highlight','#C8ED48') if re.fullmatch(r'#[0-9A-Fa-f]{6}',str(raw.get('caption_highlight','#C8ED48'))) else '#C8ED48',score=raw.get('score'),reason=str(raw.get('reason',''))[:700],selection=raw.get('selection','local'))

class Predictor(BasePredictor):
    def setup(self):
        self.whisper=None;self.loaded_model=None
    def predict(self,
        task:str=Input(default='analyze',choices=['import','analyze','render','channel','copy']),
        video_url:str=Input(default='',description='YouTube or public direct video URL'),
        video:Optional[Path]=Input(default=None,description='Upload an original video'),
        transcript_file:Optional[Path]=Input(default=None),
        edits_json:str=Input(default='[]'),
        instructions:str=Input(default=''),
        options_json:str=Input(default='{}',description='Caption branding, creator profile or social-copy context'),
        clip_count:int=Input(default=4,ge=1,le=12),
        clip_length:int=Input(default=45,ge=10,le=90),
        preview_seconds:int=Input(default=0,ge=0,le=300),
        window_start:float=Input(default=-1),
        window_end:float=Input(default=-1),
        local_model:str=Input(default='base',choices=['tiny.en','base','small','medium']),
        transcription:str=Input(default='local',choices=['local','openrouter']),
        selection:str=Input(default='local',choices=['local','openrouter']),
        render_clips:bool=Input(default=False),
        openrouter_api_key:Optional[Secret]=Input(default=None),
    )->Output:
        ai.KEY=''
        previous=getattr(self,'previous_work',None)
        if previous:shutil.rmtree(previous,ignore_errors=True)
        work=LocalPath(tempfile.mkdtemp(prefix='clipforge-'));self.previous_work=work
        options=json.loads(options_json)
        if not isinstance(options,dict):raise ValueError('Options must be a JSON object.')
        ai.KEY=openrouter_api_key.get_secret_value() if openrouter_api_key else ''
        ai.MODEL=str(options.get('model') or 'google/gemini-2.5-flash')
        ai.STT=str(options.get('stt_model') or 'openai/whisper-1')
        try:
            if task in {'channel','copy'}:
                if task=='channel':
                    public_url(video_url)
                    parsed=urlparse(video_url)
                    if parsed.hostname not in {'youtube.com','www.youtube.com'} or not re.match(r'^/(?:@[^/]+|channel/[^/]+|c/[^/]+|user/[^/]+)(?:/videos)?/?$',parsed.path):raise ValueError('Use a YouTube channel URL.')
                    video_url='https://www.youtube.com'+parsed.path.rstrip('/').removesuffix('/videos')+'/videos'
                    with yt_dlp.YoutubeDL(dict(extract_flat=True,playlistend=30,skip_download=True,quiet=True,js_runtimes={'node':{}},socket_timeout=30,retries=1)) as ydl:info=ydl.extract_info(video_url,download=False)
                    videos=[]
                    for entry in (info or {}).get('entries') or []:
                        if not entry:continue
                        url=entry.get('url') or entry.get('webpage_url') or ''
                        if re.fullmatch(r'[A-Za-z0-9_-]{11}',url):url='https://www.youtube.com/watch?v='+url
                        if url.startswith('http'):videos.append(dict(title=entry.get('title') or 'Video',url=url))
                    result={'videos':videos}
                else:result={'social':ai.social_copy(options.get('title',''),options.get('spoken',''),options.get('links',{}),options.get('profile',{}))}
                manifest=work/'manifest.json';manifest.write_text(json.dumps(result),encoding='utf-8')
                return Output(manifest=Path(manifest))
            print('Importing video',flush=True)
            if video:
                source=work/'uploaded.mp4';shutil.copyfile(str(video),source);title='Uploaded video'
            elif video_url:source,title=download(video_url,work)
            else:raise ValueError('Upload a video or provide a video URL.')
            if source.stat().st_size>2*1024**3:raise ValueError('Video exceeds the 2 GB worker limit.')
            print(f'Imported {source.stat().st_size//1024//1024} MB; preparing video',flush=True)
            meta=media.probe(source);duration=meta['duration']
            normalized=work/'source.mp4';media.normalize(source,normalized);source.unlink(missing_ok=True);source=normalized
            poster=work/'poster.jpg';media.ff('-ss',str(min(.5,duration/2)),'-i',source,'-frames:v','1','-vf','scale=640:-2','-update','1',poster)
            transcript=json.loads(LocalPath(str(transcript_file)).read_text()) if transcript_file else {'words':[],'segments':[]}
            if len(transcript.get('words',[]))>100000:raise ValueError('Transcript is too large.')
            if task=='import':raw=[]
            elif task=='render':
                raw=json.loads(edits_json)
                if not isinstance(raw,list) or not 1<=len(raw)<=12:raise ValueError('Choose 1–12 clips.')
            else:
                if not meta['has_audio']:raise ValueError('This video has no audio. Add a manual clip instead.')
                covered=min(duration,preview_seconds) if preview_seconds else duration
                if not transcript.get('words'):
                    if transcription=='openrouter':
                        transcript=ai.transcribe(source,work,covered,'openrouter',lambda msg,f:print(msg,flush=True))
                    else:
                        from faster_whisper import WhisperModel
                        if self.loaded_model!=local_model:
                            self.whisper=None;gc.collect()
                            self.whisper=WhisperModel('/opt/whisper-base' if local_model=='base' else local_model,device='cpu',compute_type='int8',cpu_threads=4,num_workers=1)
                            self.loaded_model=local_model
                        audio=work/'audio.wav';media.ff('-i',source,'-t',str(covered),'-vn','-ac','1','-ar','16000',audio)
                        words=[]
                        segments,_=self.whisper.transcribe(str(audio),word_timestamps=True,vad_filter=True,beam_size=1,condition_on_previous_text=False)
                        for segment in segments:
                            words.extend(ai.clean_words([dict(start=w.start,end=w.end,word=w.word) for w in segment.words or []],0,covered))
                            print(f'Transcribing {segment.end:.0f} / {covered:.0f} seconds',flush=True)
                        if not words:raise ValueError('No speech found in this section.')
                        transcript=dict(words=words,segments=media.segments_from_words(words),engine='replicate-whisper-'+local_model,coverage_seconds=covered,source_duration=duration,partial=covered<duration)
                        audio.unlink()
                print(f'Transcript complete: {len(transcript["words"])} words',flush=True)
                window=(window_start,window_end) if window_start>=0 and window_end>window_start else None
                raw=ai.suggest(transcript,covered,clip_count,clip_length,selection,instructions,lambda msg,f:print(msg,flush=True),window)
                raw=[dict(x,**{k:v for k,v in options.items() if k.startswith('caption_')},selection=selection) for x in raw]
            print('Preparing clip edits',flush=True)
            edits=[validate_edit(x,duration) for x in raw]
            transcript_path=work/'transcript.json';transcript_path.write_text(json.dumps(transcript,ensure_ascii=False),encoding='utf-8')
            outputs=[];posters=[]
            if task=='render' or render_clips:
                for index,edit in enumerate(edits):
                    print(f'Rendering clip {index+1}/{len(edits)}',flush=True)
                    folder=work/f'clip-{index+1}'
                    result=media.render(source,meta,edit,transcript['words'],folder,lambda msg,f:print(msg,flush=True))
                    edit['render']=result;outputs.append(Path(folder/'clip.mp4'));posters.append(Path(folder/'poster.jpg'))
            manifest=work/'manifest.json';manifest.write_text(json.dumps(dict(title=title,meta=meta,clips=edits,partial_transcript=transcript.get('partial',False)),ensure_ascii=False),encoding='utf-8')
            bundle=None
            if outputs:
                bundle=work/'clips.zip'
                with zipfile.ZipFile(bundle,'w',zipfile.ZIP_STORED) as z:
                    for index,path in enumerate(outputs):z.write(str(path),f'clip-{index+1}.mp4')
                    z.write(str(transcript_path),'transcript.json');z.write(str(manifest),'manifest.json')
            print('Processing complete; transferring output files',flush=True)
            return Output(source=Path(source) if task=='import' or not transcript_file else None,transcript=Path(transcript_path),manifest=Path(manifest),poster=Path(poster),clips=outputs,clip_posters=posters,bundle=Path(bundle) if bundle else None)
        finally:ai.KEY=''

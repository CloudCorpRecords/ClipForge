"""Media operations. All process arguments are arrays; no shell evaluation."""
import json, math, os, re, subprocess, threading, time
from pathlib import Path
import imageio_ffmpeg

FFMPEG = os.environ.get('CLIPFORGE_FFMPEG') or imageio_ffmpeg.get_ffmpeg_exe()
CTX = threading.local()

class Cancelled(Exception): pass

def check():
    if getattr(CTX, 'cancel', None) and CTX.cancel.is_set(): raise Cancelled('Cancelled')

def run(args, timeout=3600):
    check()
    import tempfile
    with tempfile.TemporaryFile() as log:
        p = subprocess.Popen([str(a) for a in args], stdout=log, stderr=subprocess.STDOUT)
        started = time.monotonic()
        try:
            while p.poll() is None:
                check()
                if time.monotonic()-started > timeout: raise RuntimeError('Processing timed out. Try a shorter clip.')
                time.sleep(.15)
        except BaseException:
            p.terminate()
            try: p.wait(timeout=3)
            except subprocess.TimeoutExpired: p.kill(); p.wait()
            raise
        log.seek(0); output = log.read().decode('utf-8', errors='replace')
        if p.returncode: raise RuntimeError(output[-2400:])
        return output

def ff(*args): return run([FFMPEG, '-hide_banner', '-nostdin', '-y', *args])

def probe(path):
    import av
    with av.open(str(path)) as c:
        videos = [s for s in c.streams if s.type == 'video']
        if not videos: raise ValueError('This file has no video track.')
        v = videos[0]
        duration = float(c.duration/av.time_base) if c.duration else float(v.duration*v.time_base)
        if not math.isfinite(duration) or not 0 < duration <= 14400: raise ValueError('Videos must be shorter than four hours.')
        return dict(duration=round(duration,3), width=v.width, height=v.height,
                    has_audio=any(s.type=='audio' for s in c.streams), fps=float(v.average_rate or 30))

def normalize(source, dest):
    import av
    with av.open(str(source)) as container:
        video=next(s for s in container.streams if s.type=='video')
        audio=next((s for s in container.streams if s.type=='audio'),None)
        compatible=(video.codec_context.name=='h264' and video.codec_context.pix_fmt=='yuv420p'
                    and video.width%2==0 and video.height%2==0)
        audio_compatible=audio is None or audio.codec_context.name=='aac'
    if compatible:
        ff('-i',source,'-map','0:v:0','-map','0:a:0?','-c:v','copy',
           '-c:a','copy' if audio_compatible else 'aac','-movflags','+faststart',dest)
        return
    ff('-i', source, '-map','0:v:0','-map','0:a:0?', '-vf','scale=trunc(iw/2)*2:trunc(ih/2)*2',
       '-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',
       '-c:a','aac','-b:a','160k','-movflags','+faststart',dest)

def stamp(t, ass=False):
    n=max(0,round(t*(100 if ass else 1000)))
    scale=100 if ass else 1000
    h,n=divmod(n,3600*scale); m,n=divmod(n,60*scale); s,ms=divmod(n,scale)
    return f'{h}:{m:02}:{s:02}.{ms:02}' if ass else f'{h:02}:{m:02}:{s:02},{ms:03}'

def segments_from_words(words):
    out=[]; group=[]
    for w in words:
        if group and (len(group)>=10 or w['start']-group[-1]['end']>.7):
            out.append(dict(start=group[0]['start'],end=group[-1]['end'],text=' '.join(x['word'] for x in group))); group=[]
        group.append(w)
        if re.search(r'[.!?]$',w['word']) and len(group)>=3:
            out.append(dict(start=group[0]['start'],end=group[-1]['end'],text=' '.join(x['word'] for x in group))); group=[]
    if group: out.append(dict(start=group[0]['start'],end=group[-1]['end'],text=' '.join(x['word'] for x in group)))
    return out

def keep_ranges(start,end,words,remove):
    if not remove: return [(start,end)]
    # Word timing defines speech intervals. Retain breaths/padding; remove gaps >0.65 s.
    intervals=[]
    for w in words:
        a=max(start,w['start']-.12); b=min(end,w['end']+.18)
        if b<=a: continue
        if intervals and a-intervals[-1][1]<.35: intervals[-1]=(intervals[-1][0],max(b,intervals[-1][1]))
        else: intervals.append((a,b))
    return intervals or [(start,end)]

def remap(t,ranges):
    elapsed=0
    for a,b in ranges:
        if t<a: return elapsed
        if t<=b: return elapsed+t-a
        elapsed+=b-a
    return elapsed

def retime_words(words,ranges):
    out=[]
    for w in words:
        for a,b in ranges:
            s=max(a,w['start']); e=min(b,w['end'])
            if e>s: out.append(dict(word=w['word'],start=remap(s,ranges),end=remap(e,ranges))); break
    return out

def escape_ass(text):
    return str(text).replace('\\','').replace('{','').replace('}','').replace('\n',' ').replace('\r',' ')

def ass_color(value,fallback='FFFFFF'):
    raw=re.sub(r'[^0-9A-Fa-f]','',str(value or ''))
    if len(raw)==3: raw=''.join(c*2 for c in raw)
    if len(raw)!=6: raw=fallback
    return f'&H00{raw[4:6]}{raw[2:4]}{raw[0:2]}'.upper()

def subtitles(words,path,width,height,style='pop',font='Arial',color='#FFFFFF',highlight='#C8ED48'):
    size=round(width*(.069 if width<height else .042)); margin=round(height*.18)
    face=re.sub(r'[^A-Za-z0-9 ]','',font or 'Arial')[:32] or 'Arial'
    primary=ass_color(color); accent=ass_color(highlight,'C8ED48')
    header=f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{face},{size},{primary},&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,{round(width*.07)},{round(width*.07)},{margin},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    lines=[]; groups=[]; group=[]
    for w in words:
        if group and (len(group)>=4 or w['start']-group[-1]['end']>.5): groups.append(group); group=[]
        group.append(w)
        if re.search(r'[.!?]$',w['word']): groups.append(group); group=[]
    if group: groups.append(group)
    for group in groups:
        if style=='clean':
            lines.append(f"Dialogue: 0,{stamp(group[0]['start'],True)},{stamp(group[-1]['end'],True)},Default,,0,0,0,,"+' '.join(escape_ass(w['word']) for w in group))
        else:
            for i,w in enumerate(group):
                a=group[0]['start'] if i==0 else w['start']; b=group[i+1]['start'] if i+1<len(group) else w['end']
                text=' '.join((f'{{\\c{accent}}}'+escape_ass(x['word']).upper()+f'{{\\c{primary}}}') if j==i else escape_ass(x['word']).upper() for j,x in enumerate(group))
                lines.append(f'Dialogue: 0,{stamp(a,True)},{stamp(b,True)},Default,,0,0,0,,{text}')
    path.write_text(header+'\n'.join(lines),encoding='utf-8')
    srt=path.with_suffix('.srt')
    srt.write_text('\n\n'.join(f"{i+1}\n{stamp(g[0]['start'])} --> {stamp(g[-1]['end'])}\n"+' '.join(w['word'] for w in g) for i,g in enumerate(groups)),encoding='utf-8')

def face_keyframes(source,start,end):
    import cv2
    cap=cv2.VideoCapture(str(source)); detector=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    out=[]; previous=.5
    try:
        for t in range(0,math.ceil(end-start),2):
            check(); cap.set(cv2.CAP_PROP_POS_MSEC,(start+t)*1000); ok,frame=cap.read()
            if not ok: continue
            h,w=frame.shape[:2]; small=cv2.resize(frame,(640,round(h*640/w)))
            faces=detector.detectMultiScale(cv2.cvtColor(small,cv2.COLOR_BGR2GRAY),1.1,5,minSize=(35,35))
            if len(faces):
                x,y,fw,fh=max(faces,key=lambda f:f[2]*f[3]); target=(x+fw/2)/640
                previous=target if not out else previous*.4+target*.6
            out.append(dict(time=float(t),x=round(previous,3),y=.5,zoom=1.0))
    finally: cap.release()
    return out or [dict(time=0,x=.5,y=.5,zoom=1)]

def expr(points,key,var='t'):
    points=sorted(points,key=lambda p:p['time']); result=str(points[-1][key])
    for a,b in reversed(list(zip(points,points[1:]))):
        dt=b['time']-a['time']
        if dt<=0: continue
        linear=f"({a[key]}+({b[key]}-{a[key]})*max(0,({var}-{a['time']}))/{dt})"
        result=f"if(lt({var},{b['time']}),{linear},{result})"
    return result

def render(source,meta,clip,words,folder,progress):
    folder.mkdir(parents=True,exist_ok=True)
    start,end=clip['start'],clip['end']; ranges=keep_ranges(start,end,words,clip['remove_silence'])
    if len(ranges)>100: raise ValueError('Too many silence cuts. Use a shorter clip or disable silence removal.')
    progress('Cutting and tightening pauses',.1)
    # Independent short encodes keep memory bounded even with many jump cuts.
    pieces=[]
    for i,(a,b) in enumerate(ranges):
        check(); part=folder/f'part-{i:03}.mp4'
        ff('-ss',str(a),'-i',source,'-t',str(b-a),'-map','0:v:0','-map','0:a:0?',
           '-vf','fps=30,scale=trunc(iw/2)*2:trunc(ih/2)*2','-c:v','libx264','-preset','veryfast','-crf','18',
           '-pix_fmt','yuv420p','-c:a','aac','-ar','48000',part)
        pieces.append(part)
    listing=folder/'concat.txt'; listing.write_text('\n'.join(f"file '{p.name}'" for p in pieces), encoding='utf-8')
    cut=folder/'cut.mp4'; ff('-f','concat','-safe','1','-i',listing,'-c','copy',cut)
    width,height={'vertical':(1080,1920),'square':(1080,1080),'landscape':(1920,1080)}[clip['aspect']]
    if clip.get('resolution')==720: width=width*2//3; height=height*2//3
    progress('Framing and animating the shot',.48)
    points=clip.get('keyframes') or (face_keyframes(source,start,end) if clip['framing']=='face' else [dict(time=0,x=clip.get('focus_x',.5),y=.5,zoom=1)])
    points=[dict(p,time=remap(start+p['time'],ranges)) for p in points]
    if clip['auto_zoom'] and not clip.get('keyframes'):
        duration=sum(b-a for a,b in ranges)
        points=[dict(p,zoom=1.0 if int(p['time']/4)%2==0 else 1.10) for p in points]
        if len(points)==1: points=[points[0],dict(points[0],time=min(4,duration),zoom=1.1),dict(points[0],time=duration,zoom=1.03)]
    # Crop to target aspect without stretching. Animate crop center before scale.
    ratio=width/height
    cropw=f'trunc(min(iw,ih*{ratio})/2)*2'; croph=f'trunc(min(ih,iw/{ratio})/2)*2'
    cx=expr(points,'x'); cy=expr(points,'y'); zoom=expr(points,'zoom','on/30')
    filters=f"crop=w='{cropw}':h='{croph}':x='max(0,min(iw-ow,iw*({cx})-ow/2))':y='max(0,min(ih-oh,ih*({cy})-oh/2))',scale={width}:{height}:flags=lanczos,setsar=1"
    if clip['framing']=='fit':
        filters=f"split[bg][fg];[bg]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},boxblur=30:3[back];[fg]scale={width}:{height}:force_original_aspect_ratio=decrease[front];[back][front]overlay=(W-w)/2:(H-h)/2,setsar=1"
    else:
        filters+=f",zoompan=z='{zoom}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={width}x{height}:fps=30"
    timed=retime_words(words,ranges); ass=folder/'captions.ass'; subtitles(timed,ass,width,height,clip.get('caption_style','pop'),clip.get('caption_font','Arial'),clip.get('caption_color','#FFFFFF'),clip.get('caption_highlight','#C8ED48'))
    if clip['captions']: filters+=",ass=captions.ass"
    output=folder/'clip.mp4'
    # Working directory makes subtitle paths safe even when project paths contain spaces.
    check(); oldcmd=[FFMPEG,'-hide_banner','-nostdin','-y','-i',str(cut),'-filter_complex',filters+'[v]',
                      '-map','[v]','-map','0:a:0?','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p']
    if meta['has_audio']: oldcmd+=['-af','loudnorm=I=-16:TP=-1.5:LRA=11','-c:a','aac','-b:a','192k']
    # Rewrite only the constant local subtitle filename, escaping ffmpeg syntax.
    safe=str(ass).replace('\\','\\\\').replace(':','\\:').replace("'","'\\''")
    oldcmd[oldcmd.index('-filter_complex')+1]=filters.replace('ass=captions.ass',f"ass=filename='{safe}'")+'[v]'
    progress('Rendering captions and final MP4',.65)
    run(oldcmd+['-movflags','+faststart',str(output)])
    ff('-ss','0.5','-i',output,'-frames:v','1','-update','1',folder/'poster.jpg')
    for p in [*pieces,cut,listing]: p.unlink(missing_ok=True)
    return dict(duration=probe(output)['duration'],width=width,height=height,range_count=len(ranges),keyframes=points)

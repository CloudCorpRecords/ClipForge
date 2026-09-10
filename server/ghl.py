import json,re,ssl,time
from datetime import datetime,timedelta,timezone
from pathlib import Path
import httpx
from fastapi import HTTPException

BASE='https://services.leadconnectorhq.com'
VERSION='v3'
SCOPES=[
    'socialplanner/account.readonly',
    'socialplanner/post.readonly',
    'socialplanner/post.write',
    'medias.write',
    'users.readonly',
]
OPTIONAL_SCOPES=['medias.readonly']

def settings_path(data:Path): return data/'ghl.json'

def load(data:Path):
    path=settings_path(data)
    if not path.exists(): return dict(token='',location='',user='',accounts=[])
    try: raw=json.loads(path.read_text(encoding='utf-8'))
    except Exception: return dict(token='',location='',user='',accounts=[])
    return dict(token=str(raw.get('token') or ''),location=str(raw.get('location') or ''),user=str(raw.get('user') or ''),accounts=list(raw.get('accounts') or []))

def save(data:Path,body:dict):
    current=load(data)
    for key in ('token','location','user'):
        if key in body and body[key] is not None: current[key]=str(body[key]).strip()
    if 'accounts' in body and body['accounts'] is not None:
        current['accounts']=[str(x).strip() for x in body['accounts'] if str(x).strip()]
    path=settings_path(data); temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(current,indent=2), encoding='utf-8'); temp.replace(path)
    return public(current)

def public(cfg):
    return dict(connected=bool(cfg.get('token') and cfg.get('location')),location=cfg.get('location') or '',user=cfg.get('user') or '',accounts=list(cfg.get('accounts') or []),scopes=SCOPES,optional_scopes=OPTIONAL_SCOPES)

def require(data:Path):
    cfg=load(data)
    if not cfg['token'] or not cfg['location']: raise HTTPException(400,'Save your GoHighLevel location ID and private integration token in Settings first.')
    if not re.fullmatch(r'[A-Za-z0-9]{10,40}',cfg['location']): raise HTTPException(400,'That location ID does not look valid.')
    return cfg

def _headers(token):
    return {'Authorization':f'Bearer {token}','Accept':'application/json','Version':VERSION}

def _detail(response):
    try:
        data=response.json()
        if isinstance(data,dict): return str(data.get('message') or data.get('error') or data.get('detail') or data)[:2000]
    except Exception: pass
    return (response.text or f'GoHighLevel returned {response.status_code}')[:2000]

def request(cfg,method,path,json_body=None,timeout=60,params=None,version=None):
    headers=_headers(cfg['token'])
    if version: headers['Version']=version
    if json_body is not None: headers['Content-Type']='application/json'
    try:
        with httpx.Client(timeout=timeout) as client:
            response=client.request(method,BASE+path,headers=headers,json=json_body,params=params)
    except httpx.HTTPError as e:
        raise HTTPException(502,f'Could not reach GoHighLevel. {e}') from e
    if response.status_code>=400: raise HTTPException(502 if response.status_code>=500 else response.status_code,_detail(response))
    if not response.content: return {}
    try: return response.json()
    except Exception: return {}

def flaky_upload(err):
    text=str(err).lower()
    return any(x in text for x in ('bad_record_mac','ssl','eof occurred','connection reset','broken pipe','timeout','temporarily unavailable','remoteprotocol'))

def upload_file(cfg,path:Path,name:str):
    if not path.is_file(): raise HTTPException(400,f'Missing file {name}.')
    size=path.stat().st_size
    if path.suffix.lower() in {'.mp4','.mov','.webm'} and size>500*1024*1024: raise HTTPException(400,'GoHighLevel video uploads are limited to 500 MB.')
    if path.suffix.lower() not in {'.mp4','.mov','.webm'} and size>25*1024*1024: raise HTTPException(400,'GoHighLevel image uploads are limited to 25 MB.')
    data={'name':name,'altId':cfg['location'],'altType':'location'}
    last=None; response=None
    for attempt in range(3):
        try:
            limits=httpx.Limits(max_keepalive_connections=0,max_connections=1)
            with path.open('rb') as handle, httpx.Client(timeout=600,http2=False,limits=limits) as client:
                response=client.post(BASE+'/medias/upload-file',headers=_headers(cfg['token']),data=data,files={'file':(name,handle,'application/octet-stream')})
            last=None; break
        except (httpx.HTTPError,ssl.SSLError) as e:
            last=e
            if attempt==2 or not flaky_upload(e): raise HTTPException(502,f'Could not upload media to GoHighLevel. {e}') from e
            time.sleep(1.5*(attempt+1))
    if last or response is None: raise HTTPException(502,f'Could not upload media to GoHighLevel. {last}')
    if response.status_code>=400: raise HTTPException(502 if response.status_code>=500 else response.status_code,_detail(response))
    try: payload=response.json()
    except Exception: raise HTTPException(502,'GoHighLevel media upload returned an invalid response.')
    url=payload.get('url') or (payload.get('file') or {}).get('url')
    file_id=payload.get('fileId') or payload.get('id') or (payload.get('file') or {}).get('id')
    if not url: raise HTTPException(502,'GoHighLevel uploaded the file but did not return a public URL.')
    return dict(url=url,fileId=file_id,name=name)

def accounts(cfg):
    data=request(cfg,'GET',f"/social-media-posting/{cfg['location']}/accounts")
    results=data.get('results') or data
    return dict(accounts=results.get('accounts') or [],groups=results.get('groups') or [])

def _normalize_user(u):
    uid=str(u.get('id') or u.get('_id') or '').strip()
    if not uid: return None
    name=' '.join(x for x in (u.get('firstName'),u.get('lastName')) if x).strip() or u.get('name') or u.get('email') or uid
    return dict(id=uid,name=name,email=u.get('email') or '',role=u.get('role') or u.get('type') or '')

def users(cfg):
    try:
        data=request(cfg,'GET','/users/',params={'locationId':cfg['location']},version='2021-07-28')
    except HTTPException:
        data=request(cfg,'GET','/users/search',params={'locationId':cfg['location']},version='2021-07-28')
    raw=data.get('users') or (data.get('results') or {}).get('users') or data.get('results') or []
    if not isinstance(raw,list): raw=[]
    out=[u for u in (_normalize_user(x) for x in raw) if u]
    if not out: raise HTTPException(400,'No staff users came back. Add users.readonly to the Private Integration, then Test connection.')
    return out

def list_posts(cfg,from_date,to_date,skip=0,limit=100):
    body=dict(type='all',skip=str(skip),limit=str(min(int(limit),100)),fromDate=from_date,toDate=to_date,includeUsers='true')
    data=request(cfg,'POST',f"/social-media-posting/{cfg['location']}/posts/list",body)
    results=data.get('results') or data
    return dict(posts=results.get('posts') or [],count=results.get('count') or len(results.get('posts') or []))

def get_post(cfg,post_id):
    data=request(cfg,'GET',f"/social-media-posting/{cfg['location']}/posts/{post_id}")
    results=data.get('results') or data
    return results.get('post') or results

def create_post(cfg,body):
    try:
        data=request(cfg,'POST',f"/social-media-posting/{cfg['location']}/posts",body)
    except HTTPException as e:
        detail=str(e.detail).lower()
        if e.status_code!=422 or 'schedule' not in detail: raise
        when=future_iso('',minutes=5)
        data=request(cfg,'POST',f"/social-media-posting/{cfg['location']}/posts",{**body,'status':'scheduled','scheduleDate':when,'selectedBestTime':when})
    results=data.get('results') or data
    return results.get('post') or results

def edit_post(cfg,post_id,body):
    data=request(cfg,'PUT',f"/social-media-posting/{cfg['location']}/posts/{post_id}",body)
    results=data.get('results') or data
    return results.get('post') or results

def delete_post(cfg,post_id):
    return request(cfg,'DELETE',f"/social-media-posting/{cfg['location']}/posts/{post_id}")

def caption(project,clip):
    title=(clip.get('title') or '').strip()
    words=[w.get('word','') for w in (project.get('transcript') or {}).get('words') or [] if clip['start']<=w.get('start',0)<clip['end'] and w.get('word')]
    spoken=' '.join(words).strip()
    spoken=re.sub(r'\s+',' ',spoken)
    if len(spoken)>1800: spoken=spoken[:1797].rsplit(' ',1)[0]+'…'
    if title and spoken: return f'{title}\n\n{spoken}'
    return title or spoken or 'New clip'

def iso(value):
    if isinstance(value,datetime):
        if value.tzinfo is None: value=value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    text=str(value or '').strip()
    if not text: raise ValueError('Pick a date and time.')
    parsed=datetime.fromisoformat(text.replace('Z','+00:00'))
    if parsed.tzinfo is None: parsed=parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')

def future_iso(value='',minutes=5):
    soon=datetime.now(timezone.utc)+timedelta(minutes=max(1,int(minutes)))
    text=str(value or '').strip()
    if not text: return iso(soon)
    try: parsed=datetime.fromisoformat(iso(text).replace('Z','+00:00'))
    except Exception: return iso(soon)
    if parsed<=datetime.now(timezone.utc)+timedelta(minutes=1): parsed=soon
    return iso(parsed)

def stagger(start,index,hours):
    base=datetime.fromisoformat(iso(start).replace('Z','+00:00'))
    return future_iso(base+timedelta(hours=max(0.0,float(hours))*index))

def media_type(path:Path):
    return {'.mp4':'video/mp4','.mov':'video/mov','.webm':'video/webm','.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png'}.get(path.suffix.lower(),'video/mp4')

def platform_of(account):
    return str(account.get('platform') or account.get('type') or '').lower()

def post_payload(cfg,accounts_list,selected_ids,summary,follow_up,schedule_date,post_type,clip,media_items,status,user_id=''):
    chosen=[a for a in accounts_list if a.get('id') in set(selected_ids)]
    if status!='draft' and not chosen: raise HTTPException(400,'Choose at least one connected social account.')
    user=str(user_id or cfg.get('user') or '').strip()
    if not user: raise HTTPException(400,'Pick who is posting. Load staff in Settings, then choose a user.')
    platforms={platform_of(a) for a in chosen}
    body=dict(accountIds=[a['id'] for a in chosen] or selected_ids,summary=summary or '',status=status,type=post_type,media=media_items,userId=user,createdBy=user)
    if status in {'scheduled','in_review'}:
        when=future_iso(schedule_date)
        body['scheduleDate']=when
        body['selectedBestTime']=when
    if follow_up: body['followUpComment']=follow_up[:1200]
    title=(clip.get('title') or 'New clip')[:100]
    if 'tiktok' in platforms:
        body['tiktokPostDetails']=dict(privacyLevel='PUBLIC_TO_EVERYONE',enableComment=True)
    if 'instagram' in platforms:
        body['instagramPostDetails']=dict(type=post_type if post_type in {'post','story','reel'} else 'reel',showOnFeed=True)
    if 'facebook' in platforms:
        body['facebookPostDetails']=dict(type=post_type if post_type in {'post','story','reel'} else 'post')
    if 'youtube' in platforms:
        body['youtubePostDetails']=dict(title=title,type='short' if post_type=='reel' else 'video',privacyLevel='public')
    if 'google' in platforms:
        body['gmbPostDetails']=dict(gmbEventType='STANDARD')
    if 'pinterest' in platforms:
        raise HTTPException(400,'Pinterest needs a board ID in GoHighLevel before ClipForge can schedule there. Uncheck Pinterest or finish board setup in GHL.')
    return body

def ensure_media(cfg,project_dir:Path,clip,progress=None):
    export=clip.get('export') or {}
    if not export or clip.get('dirty'): raise HTTPException(400,'Render this clip first so there is an MP4 to upload.')
    folder=project_dir/'exports'/export['id']
    video=folder/'clip.mp4'; poster=folder/'poster.jpg'
    stored=clip.get('ghl') or {}
    if stored.get('url') and stored.get('export_id')==export['id']:
        items=[dict(url=stored['url'],type='video/mp4',caption=clip.get('title') or 'Clip')]
        if stored.get('thumbnail'): items[0]['thumbnail']=stored['thumbnail']
        return stored,items
    if progress: progress('Uploading clip to GoHighLevel media storage',.2)
    safe=re.sub(r'[^\w -]','',clip.get('title') or 'clip')[:40] or 'clip'
    video_file=upload_file(cfg,video,f'{safe}.mp4')
    thumb=None
    if poster.is_file():
        if progress: progress('Uploading thumbnail to media storage',.45)
        thumb=upload_file(cfg,poster,'poster.jpg')
    stored=dict(url=video_file['url'],fileId=video_file.get('fileId'),thumbnail=(thumb or {}).get('url'),thumbId=(thumb or {}).get('fileId'),export_id=export['id'],uploaded=time.time())
    items=[dict(url=stored['url'],type=media_type(video),caption=clip.get('title') or 'Clip')]
    if stored.get('thumbnail'): items[0]['thumbnail']=stored['thumbnail']
    return stored,items

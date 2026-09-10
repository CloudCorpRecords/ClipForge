import importlib,json
import pytest
from fastapi.testclient import TestClient
s=importlib.import_module('server.app')

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(s,'DATA',tmp_path)
    monkeypatch.setattr(s,'JOBS',{})
    return TestClient(s.app)
H={'X-ClipForge':'1'}

def test_folder_video_crud_and_prompt(client):
    f=client.post('/api/folders',headers=H,json={'name':'Garden','instructions':'Use warm stories','channel_url':'https://www.youtube.com/@garden'}).json()
    p=s.create('My video',f['id'])
    assert s.project_profile(p)['folder_instructions']=='Use warm stories'
    assert client.put('/api/projects/'+p['id'],headers=H,json={'title':'New title','folder_id':None}).status_code==200
    assert s.read(p['id'])['folder_id'] is None
    assert client.put('/api/folders/'+f['id'],headers=H,json={'name':'New garden','instructions':'Practical tips'}).json()['instructions']=='Practical tips'
    client.put('/api/projects/'+p['id'],headers=H,json={'folder_id':f['id']})
    assert client.delete('/api/folders/'+f['id'],headers=H).status_code==200
    assert s.read(p['id'])['folder_id'] is None
    assert client.delete('/api/projects/'+p['id'],headers=H).status_code==200
    assert client.get('/api/projects').json()==[]
    assert client.post('/api/trash/'+p['id']+'/restore',headers=H,json={}).json()['title']=='New title'

def test_busy_video_cannot_be_deleted(client):
    p=s.create('Busy');s.JOBS['x']={'project':p['id'],'state':'running'}
    assert client.delete('/api/projects/'+p['id'],headers=H).status_code==409
    assert s.read(p['id'])['title']=='Busy'

def test_downloader_arguments_parse_without_separator(client,monkeypatch,tmp_path):
    import yt_dlp
    seen=[]
    monkeypatch.setattr(s,'validate_url',lambda u:u)
    monkeypatch.setattr(s,'queue',lambda pid,kind,work:work(lambda *a:None))
    monkeypatch.setattr(s,'finish_import',lambda *a:None)
    def run(args):
        parsed=yt_dlp.parse_options(args[3:])
        assert '--' not in args
        assert parsed.urls==['https://www.youtube.com/watch?v=bOfEcq3vcH8']
        from pathlib import Path
        dest=Path(args[args.index('-o')+1]).parent
        (dest/'download.info.json').write_text(json.dumps({'title':'Test'}))
        (dest/'download.mp4').touch();seen.append(args);return ''
    monkeypatch.setattr(s.media,'run',run)
    client.post('/api/import/url',headers=H,json={'url':'https://www.youtube.com/watch?v=bOfEcq3vcH8'})
    assert seen

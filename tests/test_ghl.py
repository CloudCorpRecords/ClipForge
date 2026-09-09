import json
from pathlib import Path
from fastapi.testclient import TestClient
from server.app import app
from server import ghl

def test_caption_uses_title_and_clip_words():
    project={'transcript':{'words':[dict(start=1,end=2,word='Hello'),dict(start=2,end=3,word='world'),dict(start=10,end=11,word='later')]}}
    clip={'title':'Hook','start':0,'end':5}
    assert ghl.caption(project,clip)=='Hook\n\nHello world'

def test_stagger_keeps_utc_spacing():
    assert ghl.stagger('2026-12-01T09:00:00Z',2,6)=='2026-12-01T21:00:00.000Z'

def test_future_iso_moves_past_times_ahead():
    assert ghl.future_iso('1999-01-01T00:00:00Z') > '2020-01-01T00:00:00.000Z'
    assert ghl.future_iso('').endswith('Z')

def test_ghl_settings_persist(tmp_path):
    saved=ghl.save(tmp_path,{'token':'pit-test','location':'Your location ID','accounts':['acct1']})
    assert saved['connected'] is True
    assert saved['location']=='Your location ID'
    assert 'token' not in saved
    loaded=ghl.load(tmp_path)
    assert loaded['token']=='pit-test'
    assert json.loads(Path(tmp_path,'ghl.json').read_text())['accounts']==['acct1']

def test_ssl_mac_error_is_retryable():
    assert ghl.flaky_upload('[SSL: SSLV3_ALERT_BAD_RECORD_MAC] sslv3 alert bad record mac')
    assert not ghl.flaky_upload('401 unauthorized')

def test_ghl_routes_need_settings(tmp_path):
    from fastapi import HTTPException
    try: ghl.require(tmp_path)
    except HTTPException as e: assert e.status_code==400
    else: raise AssertionError('expected missing settings')
    health=TestClient(app).get('/api/health').json()
    assert 'users.readonly' in health['ghl']['scopes']

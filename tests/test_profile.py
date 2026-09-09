import importlib
from fastapi.testclient import TestClient
from server import ai

server = importlib.import_module('server.app')

def test_profile_roundtrip_partial_update_and_clear_links(tmp_path, monkeypatch):
    monkeypatch.setattr(server, 'DATA', tmp_path)
    monkeypatch.setattr(server, 'PROFILE', {})
    monkeypatch.setattr(server, 'LINKS', dict(site='', course=''))
    monkeypatch.setattr(ai, 'KEY', '')
    client = TestClient(server.app)
    headers = {'X-ClipForge':'1'}
    profile = dict(name='Garden Studio', about='Balcony gardening', audience='Beginners', tone='Warm', offer='A $15 guide', cta='Get the guide', avoid='No guarantees')
    response = client.post('/api/settings', headers=headers, json={'profile':profile,'site_url':'https://garden.example','course_url':'https://garden.example/guide'})
    assert response.status_code == 200
    assert response.json()['profile'] == profile
    client.post('/api/settings', headers=headers, json={'key':''})
    assert client.get('/api/health').json()['profile'] == profile
    server.PROFILE.clear()
    server.load_ai()
    assert server.PROFILE == profile
    response = client.post('/api/settings', headers=headers, json={'site_url':'','course_url':'','profile':{}})
    assert response.json()['links'] == dict(site='',course='')
    assert response.json()['profile']['name'] == ''

def test_cloud_copy_receives_profile_and_local_fallback_has_no_unrelated_ads(monkeypatch):
    profile = dict(name='Garden Studio', tone='Calm', offer='A $15 guide', avoid='No promises', cta='Read my guide')
    seen = []
    monkeypatch.setattr(ai,'KEY','test')
    def request(endpoint, body):
        seen.append(body)
        raise RuntimeError('offline')
    monkeypatch.setattr(ai,'request',request)
    result=ai.social_copy('Fresh herbs','Grow herbs on a balcony',{},profile)
    assert 'Garden Studio' in seen[0]['messages'][1]['content']
    assert 'No promises' in seen[0]['messages'][1]['content']
    text=' '.join(item['text'] for item in result['posts']+result['comments'])
    assert 'Garden Studio' in text
    assert not any(value in text for value in ['example.com','Card Price King','Aspire','https://','$7'])
    assert result['_context'] != ai.social_context({},dict(name='Another creator'))

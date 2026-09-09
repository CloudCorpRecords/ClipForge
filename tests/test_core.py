import pytest
from fastapi.testclient import TestClient
from server.app import app,Clip,validate_url
from server.media import keep_ranges,remap,retime_words,escape_ass,expr,ass_color
from server.ai import local_social
WORDS=[dict(start=1,end=2,word='Hello'),dict(start=4,end=5,word='world')]
def test_silence_remapping_preserves_words_and_timing():
    ranges=keep_ranges(0,6,WORDS,True)
    assert len(ranges)==2
    out=retime_words(WORDS,ranges)
    assert [x['word'] for x in out]==['Hello','world']
    assert out[0]['start']==pytest.approx(.12)
    assert out[1]['start']==pytest.approx(1.42)
    assert out[1]['end']-out[1]['start']==pytest.approx(1)
    assert remap(6,ranges)==pytest.approx(2.6)
def test_partial_word_trim():
    assert retime_words(WORDS,[(1.5,4.5)])==[dict(start=0,end=.5,word='Hello'),dict(start=2.5,end=3,word='world')]
@pytest.mark.parametrize('data',[dict(start=3,end=2),dict(start=-1,end=4),dict(start=0,end=float('nan')),dict(start=0,end=900),dict(start=0,end=10,keyframes=[dict(time=11)]),dict(start=0,end=10,keyframes=[dict(time=1),dict(time=1)])])
def test_invalid_edits_rejected(data):
    with pytest.raises(ValueError): Clip(**data)
def test_caption_override_injection_removed():
    assert escape_ass('{\\pos(0,0)}test\nnext')=='pos(0,0)test next'
def test_cross_origin_and_host_rejected():
    c=TestClient(app)
    assert c.post('/api/settings',json={'key':'test'},headers={'Origin':'https://evil.test','X-ClipForge':'1'}).status_code==403
    assert c.post('/api/settings',json={'key':'test'}).status_code==403
    assert c.get('/api/health',headers={'Host':'evil.test'}).status_code==403
    assert c.get('/api/health').status_code==200

def test_installed_extension_origin_has_strict_cors_access():
    c=TestClient(app)
    origin='chrome-extension://hllhhgmemaeimjjecboegbfgbkbehokk'
    preflight=c.options('/api/health',headers={
        'Origin':origin,
        'Access-Control-Request-Method':'GET',
        'Access-Control-Request-Headers':'X-ClipForge',
    })
    assert preflight.status_code==204
    assert preflight.headers['access-control-allow-origin']==origin
    response=c.get('/api/health',headers={'Origin':origin,'X-ClipForge':'1'})
    assert response.status_code==200
    assert response.headers['access-control-allow-origin']==origin
def test_local_url_rejected():
    with pytest.raises(ValueError): validate_url('http://127.0.0.1/private')
    with pytest.raises(ValueError): validate_url('file:///etc/passwd')
def test_crop_interpolation_bounded_before_first_point():
    assert 'max(0' in expr([dict(time=2,x=.2),dict(time=4,x=.8)],'x')
def test_ass_color_is_bgr():
    assert ass_color('#C8ED48')=='&H0048EDC8'
def test_local_social_has_options_and_links():
    out=local_social('Hook','sell more cards','https://example.com','https://example.com/course')
    assert len(out['posts'])==3 and len(out['comments'])==3
    blob=' '.join(x['text'] for x in out['posts']+out['comments'])
    assert 'cardpriceking.com' in blob and 'bulk-selling' in blob

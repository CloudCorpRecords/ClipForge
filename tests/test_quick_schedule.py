import importlib
import pytest
from pydantic import ValidationError
s=importlib.import_module('server.app')

def test_batch_keeps_chosen_copy_blank_comment_and_order(monkeypatch):
    project={'clips':[{'id':'a','export':{'id':'e1'}},{'id':'b','export':{'id':'e2'}}]}
    monkeypatch.setattr(s,'require_ready',lambda pid:project)
    monkeypatch.setattr(s,'queue',lambda pid,kind,work:work(lambda *args:None))
    monkeypatch.setattr(s,'clip_social',lambda *a:pytest.fail('Reviewed copy must not be regenerated'))
    sent=[]
    monkeypatch.setattr(s,'publish_clip',lambda p,c,item,progress:sent.append((c['id'],item)))
    s.publish_many('p',s.GhlQuick(clip_ids=['b','a'],account_ids=['social'],start='2030-01-01T12:00:00Z',interval_hours=6,posts=[{'clip_id':'a','summary':'My A title','follow_up':'My A comment'},{'clip_id':'b','summary':'My B title','follow_up':''}]))
    assert [c for c,p in sent]==['b','a']
    assert sent[0][1].summary=='My B title'
    assert sent[0][1].follow_up==''
    assert sent[1][1].follow_up=='My A comment'
    assert '18:00:00' in sent[1][1].schedule_date

@pytest.mark.parametrize('posts',[[{'clip_id':'a','summary':'a'}],[{'clip_id':'a','summary':'a'},{'clip_id':'a','summary':'b'}]])
def test_batch_requires_exactly_one_review_per_clip(posts):
    with pytest.raises(ValidationError):
        s.GhlQuick(clip_ids=['a','b'],account_ids=['social'],start='2030-01-01T12:00:00Z',posts=posts)

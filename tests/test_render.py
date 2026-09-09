from server import media

def test_actual_vertical_export_with_captions_and_jump_cut(tmp_path):
    source=tmp_path/'input.mp4'
    media.ff('-f','lavfi','-i','testsrc2=size=640x360:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','5','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',source)
    words=[dict(start=.2,end=1.1,word='Caption'),dict(start=1.2,end=1.8,word='timing'),dict(start=3.5,end=4.5,word='works.')]
    c=dict(start=0,end=5,remove_silence=True,aspect='vertical',resolution=720,framing='center',focus_x=.5,keyframes=[dict(time=0,x=.4,y=.5,zoom=1),dict(time=5,x=.6,y=.5,zoom=1.1)],auto_zoom=True,captions=True,caption_style='pop')
    folder=tmp_path/'export';result=media.render(source,media.probe(source),c,words,folder,lambda *a:None)
    info=media.probe(folder/'clip.mp4')
    assert (info['width'],info['height'])==(720,1280)
    assert info['has_audio'] and 2.5<info['duration']<4
    assert result['range_count']==2
    assert 'Caption' in (folder/'captions.srt').read_text()
    assert 'Dialogue:' in (folder/'captions.ass').read_text()
    media.ff('-v','error','-i',folder/'clip.mp4','-f','null','-')

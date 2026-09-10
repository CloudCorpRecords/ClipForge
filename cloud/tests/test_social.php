<?php
require __DIR__.'/../php/social.php';
function check($yes){if(!$yes)throw new RuntimeException('Social payload regression');}
$accounts=[['id'=>'youtube-account','platform'=>'youtube']];
$clip=['title'=>'My chosen title','ghl'=>['url'=>'https://example.com/clip.mp4']];
$body=['account_ids'=>['youtube-account'],'user_id'=>'test-user','summary'=>'My reviewed caption','follow_up'=>'My first comment','schedule_date'=>'2030-01-01T12:00:00Z'];
$p=socialPayload([],$accounts,$clip,$body);
check($p['summary']===$body['summary']);check($p['followUpComment']===$body['follow_up']);check($p['youtubePostDetails']['title']===$clip['title']);check($p['scheduleDate']==='2030-01-01T12:00:00.000Z');
$body['follow_up']='';check(!isset(socialPayload([],$accounts,$clip,$body)['followUpComment']));
$body['account_ids']=['missing'];$rejected=false;try{socialPayload([],$accounts,$clip,$body);}catch(RuntimeException $e){$rejected=true;}check($rejected);
echo "Social payload checks passed; no posts sent.\n";

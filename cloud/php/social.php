<?php
function socialPublic():array {$c=config();return ['connected'=>!empty($c['ghl_token'])&&!empty($c['ghl_location']),'location'=>$c['ghl_location']??'','user'=>$c['ghl_user']??'','accounts'=>$c['ghl_accounts']??[],'scopes'=>['socialplanner/account.readonly','socialplanner/post.readonly','socialplanner/post.write','medias.write','users.readonly']];}
function socialConfig():array {$c=config();if(empty($c['ghl_token'])||!preg_match('/^[A-Za-z0-9]{10,40}$/',$c['ghl_location']??''))throw new RuntimeException('Save your Social Planner location ID and Private Integration token in AI & settings.');return $c;}
function socialRequest(string $method,string $path,?array $body=null,string $version='v3',bool $multipart=false):array {
 $c=socialConfig();$h=curl_init('https://services.leadconnectorhq.com'.$path);$headers=['Authorization: Bearer '.$c['ghl_token'],'Version: '.$version,'Accept: application/json'];if(!$multipart)$headers[]='Content-Type: application/json';
 curl_setopt_array($h,[CURLOPT_RETURNTRANSFER=>true,CURLOPT_CUSTOMREQUEST=>$method,CURLOPT_HTTPHEADER=>$headers,CURLOPT_TIMEOUT=>$multipart?600:60]);if($body!==null)curl_setopt($h,CURLOPT_POSTFIELDS,$multipart?$body:json_encode($body));$raw=curl_exec($h);$code=curl_getinfo($h,CURLINFO_RESPONSE_CODE);if($raw===false)throw new RuntimeException('Social Planner connection failed.');$out=json_decode($raw,true)??[];if($code>=400)throw new RuntimeException('Social Planner '.$code.': '.substr(is_string($out['message']??null)?$out['message']:json_encode($out),0,1200));return $out;
}
function socialApi(array $s,array $q,array $b,string $method):array {
 $c=socialConfig();$base='/social-media-posting/'.$c['ghl_location'];
 if(($s[1]??'')==='accounts'){$d=socialRequest('GET',$base.'/accounts');$r=$d['results']??$d;return ['accounts'=>$r['accounts']??[],'groups'=>$r['groups']??[]];}
 if(($s[1]??'')==='users'){
  try{$d=socialRequest('GET','/users/?locationId='.rawurlencode($c['ghl_location']),null,'2021-07-28');}catch(Throwable $e){$d=socialRequest('GET','/users/search?locationId='.rawurlencode($c['ghl_location']),null,'2021-07-28');}
  $raw=$d['users']??$d['results']['users']??$d['results']??[];$users=[];foreach($raw as $u){$id=$u['id']??$u['_id']??'';if($id)$users[]=['id'=>$id,'name'=>trim(($u['firstName']??'').' '.($u['lastName']??''))?:($u['name']??$u['email']??$id),'email'=>$u['email']??''];}if(!$users)throw new RuntimeException('No staff users returned. Add users.readonly to the integration.');return ['users'=>$users];
 }
 if(($s[1]??'')!=='posts')throw new RuntimeException('Unknown Social Planner action.');
 if(empty($s[2])){$d=socialRequest('POST',$base.'/posts/list',['type'=>'all','skip'=>'0','limit'=>'100','fromDate'=>$q['from_date']??'','toDate'=>$q['to_date']??'','includeUsers'=>'true']);$r=$d['results']??$d;return ['posts'=>$r['posts']??[],'count'=>$r['count']??0];}
 $path=$base.'/posts/'.rawurlencode($s[2]);
 if($method==='DELETE')return socialRequest('DELETE',$path);
 if($method==='PUT'){$when=socialDate($b['schedule_date']??'');$existing=socialRequest('GET',$path);$r=$existing['results']??$existing;$post=$r['post']??$r;$payload=array_intersect_key($post,array_flip(['accountIds','summary','media','type','followUpComment','userId','tiktokPostDetails','instagramPostDetails','facebookPostDetails','youtubePostDetails','gmbPostDetails','linkedinPostDetails']));$payload['status']='scheduled';$payload['scheduleDate']=$when;$payload['selectedBestTime']=$when;$payload['scheduleTimeUpdated']=true;if(!empty($c['ghl_user']))$payload['userId']=$c['ghl_user'];$d=socialRequest('PUT',$path,$payload);}
 else $d=socialRequest('GET',$path);$r=$d['results']??$d;return $r['post']??$r;
}
function socialDate(string $value):string {try{$d=new DateTimeImmutable($value?:'+5 minutes');}catch(Throwable $e){throw new RuntimeException('Choose a valid date and time.');}if($d->getTimestamp()<time()+60)$d=new DateTimeImmutable('+5 minutes');return $d->setTimezone(new DateTimeZone('UTC'))->format('Y-m-d\TH:i:s.000\Z');}
function socialMedia(array $p,array $clip):array {
 if(empty($clip['export'])||!empty($clip['dirty']))throw new RuntimeException('Render the clip first.');
 if(!empty($clip['ghl']['url'])&&($clip['ghl']['export_id']??'')===$clip['export']['id'])return $clip;
 $c=socialConfig();$dir=PRIVATE_DIR.'/assets/'.$p['id'].'/exports/'.identifier($clip['export']['id']);$file=$dir.'/clip.mp4';if(!is_file($file)||filesize($file)>500*1024**2)throw new RuntimeException('Social video upload must be under 500 MB.');
 $d=socialRequest('POST','/medias/upload-file',['name'=>substr($clip['title'],0,60).'.mp4','altId'=>$c['ghl_location'],'altType'=>'location','file'=>new CURLFile($file,'video/mp4','clip.mp4')],'v3',true);$url=$d['url']??$d['file']['url']??null;if(!$url)throw new RuntimeException('Social media upload returned no URL.');
 $clip['ghl']=['url'=>$url,'fileId'=>$d['fileId']??$d['id']??null,'export_id'=>$clip['export']['id'],'uploaded'=>time()];return $clip;
}
function socialPayload(array $cfg,array $accounts,array $clip,array $body):array {
 $ids=$body['account_ids']??[];if(!is_array($ids)||!$ids)throw new RuntimeException('Choose at least one social account.');$chosen=array_values(array_filter($accounts,fn($a)=>in_array($a['id'],$ids,true)));if(count($chosen)!==count(array_unique($ids)))throw new RuntimeException('A selected social account is no longer connected.');
 $user=$body['user_id']??$cfg['ghl_user']??'';if(!$user)throw new RuntimeException('Pick who is posting.');$type=$body['type']??'reel';$status=$body['status']??'scheduled';if(!in_array($status,['scheduled','published','draft','in_review'])||!in_array($type,['reel','post','story']))throw new RuntimeException('Invalid post type or status.');
 $out=['accountIds'=>array_column($chosen,'id'),'summary'=>substr($body['summary']??'',0,5000),'status'=>$status,'type'=>$type,'media'=>[['url'=>$clip['ghl']['url'],'type'=>'video/mp4','caption'=>$clip['title']]],'userId'=>$user,'createdBy'=>$user];
 if(in_array($status,['scheduled','in_review']))$out['scheduleDate']=$out['selectedBestTime']=socialDate($body['schedule_date']??'');if(!empty($body['follow_up']))$out['followUpComment']=substr($body['follow_up'],0,1200);
 foreach($chosen as $a){$platform=strtolower($a['platform']??$a['type']??'');if($platform==='pinterest')throw new RuntimeException('Set a Pinterest board in Social Planner before scheduling there.');if($platform==='tiktok')$out['tiktokPostDetails']=['privacyLevel'=>'PUBLIC_TO_EVERYONE','enableComment'=>true];if($platform==='instagram')$out['instagramPostDetails']=['type'=>$type,'showOnFeed'=>true];if($platform==='facebook')$out['facebookPostDetails']=['type'=>$type];if($platform==='youtube')$out['youtubePostDetails']=['title'=>substr($clip['title'],0,100),'type'=>$type==='reel'?'short':'video','privacyLevel'=>'public'];if($platform==='google')$out['gmbPostDetails']=['gmbEventType'=>'STANDARD'];}
 return $out;
}
function socialPublish(array $p,int $index,array $body):void {
 $cfg=socialConfig();$accounts=socialApi(['ghl','accounts'],[],[],'GET')['accounts'];$clip=$p['clips'][$index];
 // Validate choices before transferring video.
 socialPayload($cfg,$accounts,array_merge($clip,['ghl'=>['url'=>'pending']]),$body);
 $key=hash('sha256',json_encode([$clip['id'],$clip['export']['id']??'', $body]));$sent=$p['social_submissions'][$key]??null;if($sent==='done')return;if($sent==='pending')throw new RuntimeException('This submission has an uncertain result. Check Social Planner before retrying to avoid a duplicate.');
 $clip=socialMedia($p,$clip);$p['clips'][$index]=$clip;saveProject($p);$payload=socialPayload($cfg,$accounts,$clip,$body);$p['social_submissions'][$key]='pending';saveProject($p);
 $d=socialRequest('POST','/social-media-posting/'.$cfg['ghl_location'].'/posts',$payload);$r=$d['results']??$d;$post=$r['post']??$r;
 $p['clips'][$index]['ghl']['posts'][]=['id'=>$post['_id']??$post['id']??null,'status'=>$payload['status'],'scheduleDate'=>$payload['scheduleDate']??null,'summary'=>$payload['summary']];$p['social_submissions'][$key]='done';saveProject($p);
 $cfg['ghl_accounts']=$body['account_ids'];$cfg['ghl_user']=$payload['userId'];store('config.json',$cfg);
}
function socialBatch(array $p,array $body):array {
 $ids=$body['clip_ids']??[];$posts=$body['posts']??[];if(!is_array($ids)||!count($ids)||count($ids)>12||count(array_unique($ids))!==count($ids))throw new RuntimeException('Select up to 12 unique clips.');
 $by=[];foreach($posts as $post){$cid=$post['clip_id']??'';if(isset($by[$cid]))throw new RuntimeException('Duplicate post review.');$by[$cid]=$post;}if(count($by)!==count($ids)||array_diff($ids,array_keys($by)))throw new RuntimeException('Review the title and first comment for every selected clip.');
 $items=[];$cfg=socialConfig();$accounts=socialApi(['ghl','accounts'],[],[],'GET')['accounts'];$start=new DateTimeImmutable(socialDate($body['start']??''));
 foreach($ids as $i=>$cid){$index=null;foreach($p['clips'] as $n=>$clip)if($clip['id']===$cid){$index=$n;break;}if($index===null||empty($p['clips'][$index]['export'])||!empty($p['clips'][$index]['dirty']))throw new RuntimeException('Render every selected clip before scheduling.');$when=$start->modify('+'.(int)(max(0,(float)($body['interval_hours']??6))*3600*$i).' seconds');$item=['account_ids'=>$body['account_ids']??[],'user_id'=>$body['user_id']??'','summary'=>$by[$cid]['summary']??'','follow_up'=>$by[$cid]['follow_up']??'','schedule_date'=>$when->format(DATE_ATOM),'status'=>'scheduled','type'=>$body['type']??'reel'];socialPayload($cfg,$accounts,array_merge($p['clips'][$index],['ghl'=>['url'=>'pending']]),$item);$items[]=[$index,$item];}
 foreach($items as [$index,$item])socialPublish(project($p['id']),$index,$item);return studioDone(project($p['id']),'publish','Your reviewed lineup is scheduled.');
}

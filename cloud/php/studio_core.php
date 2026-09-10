<?php
function studioClip(array $raw,float $duration):array {
 $start=(float)($raw['start']??0);$end=(float)($raw['end']??30);
 if(!is_finite($start)||!is_finite($end)||$start<0||$end>$duration+.1||$end-$start<1||$end-$start>180)throw new RuntimeException('Clips must be 1–180 seconds and inside the video.');
 $defaults=['id'=>id(),'title'=>'New clip','aspect'=>'vertical','framing'=>'face','focus_x'=>.5,'keyframes'=>[],'resolution'=>1080,'auto_zoom'=>true,'remove_silence'=>true,'captions'=>true,'caption_style'=>'pop','caption_font'=>'Arial','caption_color'=>'#FFFFFF','caption_highlight'=>'#C8ED48','dirty'=>true,'selection'=>'manual','score'=>null,'reason'=>'Manual selection'];
 $c=array_merge($defaults,$raw,['start'=>$start,'end'=>$end]);identifier($c['id']);
 if(!in_array($c['aspect'],['vertical','square','landscape'])||!in_array($c['framing'],['face','center','fit']))throw new RuntimeException('Choose a valid canvas and framing.');
 if(!is_array($c['keyframes'])||count($c['keyframes'])>50)throw new RuntimeException('Use at most 50 keyframes.');
 foreach($c['keyframes'] as $k){foreach(['time','x','y','zoom'] as $field)if(!isset($k[$field])||!is_numeric($k[$field])||!is_finite((float)$k[$field]))throw new RuntimeException('Invalid keyframe.');if($k['time']<0||$k['time']>$end-$start||$k['x']<0||$k['x']>1||$k['y']<0||$k['y']>1||$k['zoom']<1||$k['zoom']>2)throw new RuntimeException('Keyframe is outside the clip or crop.');}
 $c['title']=substr(trim((string)$c['title']),0,120);return $c;
}
function studioProject(array $p):array {
 $changed=false;$dir=PRIVATE_DIR.'/assets/'.$p['id'];
 foreach($p['clips'] as $i=>&$c){if(empty($c['id'])){$c=studioClip($c,(float)$p['meta']['duration']);$changed=true;}if(!empty($c['file'])&&empty($c['export'])&&is_file($dir.'/'.$c['file'])){$eid=id();mkdir($dir.'/exports/'.$eid,0700,true);copy($dir.'/'.$c['file'],$dir.'/exports/'.$eid.'/clip.mp4');$c['export']=['id'=>$eid]+($c['render']??['duration'=>$c['end']-$c['start']]);$c['dirty']=false;$changed=true;}}unset($c);
 if($changed)saveProject($p);
 $p['state']=is_file($dir.'/source.mp4')?'ready':(in_array($p['status'],['failed','canceled'])?'error':'importing');
 if(is_file($dir.'/transcript.json'))$p['transcript']=json_decode(file_get_contents($dir.'/transcript.json'),true);
 $p=publicProject($p);unset($p['job'],$p['pending']);return $p;
}
function studioJob(array $p):array {
 $j=$p['job']??['id'=>$p['prediction']??$p['id'],'kind'=>'process'];$j['project']=$p['id'];
 $j['state']=match($p['status']){'ready'=>'done','failed'=>'error','canceled'=>'cancelled','starting'=>'queued',default=>'running'};
 $stage=publicProject($p)['stage'];$j['message']=$p['error']??'';if(!$j['message'])$j['message']=$stage?:($j['state']==='done'?'Ready · saved to your website':($p['status']==='saving'?'Saving cloud output files…':'Replicate · '.$p['status']));
 $j['progress']=in_array($j['state'],['done','error','cancelled'])?1:($p['status']==='saving'?.95:.2);
 if(preg_match('~Transcribing ([0-9]+) / ([0-9]+)~',$stage,$m)&&$m[2]>0)$j['progress']=.1+.65*$m[1]/$m[2];return $j;
}
function studioIdle(array $p):void {if(!in_array($p['status'],['ready','failed','canceled']))throw new RuntimeException('Wait for this project to finish processing.');}
function studioStart(array $p,array $input,string $kind,array $pending=[]):array {
 studioIdle($p);$j=startPrediction($input);$p['prediction']=$j['id'];$p['status']=$j['status'];$p['error']='';$p['logs']='';$p['job']=['id'=>id(),'kind'=>$kind];$p['pending']=['kind'=>$kind]+$pending;saveProject($p);return studioJob($p);
}
function studioDone(array $p,string $kind,string $message='Saved'):array {$p['status']='ready';$p['error']='';$p['logs']='';$p['job']=['id'=>id(),'kind'=>$kind];saveProject($p);$j=studioJob($p);$j['message']=$message;return $j;}
function cloudSync(string $id):array {
 $lock=fopen(PRIVATE_DIR.'/lock-'.identifier($id),'c');if(!flock($lock,LOCK_EX|LOCK_NB))return project($id);
 try{
  $p=project($id);if(empty($p['prediction'])||in_array($p['status'],['ready','failed','canceled']))return $p;
  $job=replicate('GET','predictions/'.rawurlencode($p['prediction']));$p['status']=$job['status'];$p['logs']=substr($job['logs']??'',-6000);$p['error']=$job['error']??'';
  if($job['status']==='succeeded'){
   $p['status']='saving';saveProject($p);$dir=PRIVATE_DIR.'/assets/'.$id;if(!is_dir($dir))mkdir($dir,0700,true);$out=$job['output'];if(!is_array($out))throw new RuntimeException('Prediction output expired or unavailable.');
   foreach(['source'=>'source.mp4','transcript'=>'transcript.json','manifest'=>'manifest.json','poster'=>'poster.jpg'] as $key=>$file)if(!empty($out[$key]))saveRemote($out[$key],$dir.'/'.$file);
   if(!is_file($dir.'/source.mp4')||!is_file($dir.'/manifest.json'))throw new RuntimeException('Missing video or manifest output.');
   $manifest=json_decode(file_get_contents($dir.'/manifest.json'),true,512,JSON_THROW_ON_ERROR);$pending=$p['pending']??[];$kind=$pending['kind']??'replace';
   $p['title']=$p['custom_title']??($kind==='import'||empty($p['meta'])?$manifest['title']:$p['title']);$p['meta']=$manifest['meta'];$p['partial_transcript']=$manifest['partial_transcript']??false;$fresh=[];
   foreach($manifest['clips']??[] as $i=>$raw){$raw['id']=$pending['clip_ids'][$i]??id();$c=studioClip($raw,(float)$p['meta']['duration']);$c['dirty']=true;
    if(!empty($out['clips'][$i])){$eid=id();$edir=$dir.'/exports/'.$eid;mkdir($edir,0700,true);saveRemote($out['clips'][$i],$edir.'/clip.mp4');if(!empty($out['clip_posters'][$i]))saveRemote($out['clip_posters'][$i],$edir.'/poster.jpg');elseif(is_file($dir.'/poster.jpg'))copy($dir.'/poster.jpg',$edir.'/poster.jpg');$c['export']=['id'=>$eid]+($raw['render']??['duration'=>$c['end']-$c['start']]);$c['dirty']=false;}
    $fresh[]=$c;
   }
   if($kind==='analyze')$p['clips']=array_merge($p['clips'],$fresh);
   elseif($kind==='render'){foreach($fresh as $c){foreach($p['clips'] as &$old)if($old['id']===$c['id']){$old=array_merge($old,$c);unset($old['social']);break;}unset($old);}}
   elseif($kind!=='import')$p['clips']=$fresh;
   if(!empty($out['bundle']))saveRemote($out['bundle'],$dir.'/clips.zip');
   $p['status']='ready';$p['logs']='';$p['completed']=time();unset($p['pending']);
  }
  saveProject($p);return $p;
 }finally{flock($lock,LOCK_UN);fclose($lock);}
}
function studioOptions():array {$c=config();return ['model'=>$c['model']??'google/gemini-2.5-flash','stt_model'=>$c['stt_model']??'openai/whisper-1'];}
function studioProfile(array $p):array {$profile=readStore('profile.json');foreach(readStore('folders.json') as $f)if($f['id']===($p['folder_id']??''))$profile['folder_instructions']=$f['instructions']??'';return $profile;}
function smallPrediction(array $input):array {
 $job=startPrediction($input);$deadline=time()+600;
 while(in_array($job['status'],['starting','processing'])){if(time()>$deadline){replicate('POST','predictions/'.$job['id'].'/cancel',[]);throw new RuntimeException('Cloud request timed out. Try again.');}sleep(2);$job=replicate('GET','predictions/'.$job['id']);}
 if($job['status']!=='succeeded')throw new RuntimeException($job['error']??'Cloud request failed.');
 $path=PRIVATE_DIR.'/result-'.id().'.json';try{saveRemote($job['output']['manifest'],$path);return json_decode(file_get_contents($path),true,512,JSON_THROW_ON_ERROR);}finally{@unlink($path);}
}
function studioBundle(string $pid):string {$p=project($pid);$dir=PRIVATE_DIR.'/assets/'.$pid;$path=$dir.'/all-clips.zip';$zip=new ZipArchive();if($zip->open($path,ZipArchive::CREATE|ZipArchive::OVERWRITE)!==true)throw new RuntimeException('Could not create ZIP.');$count=0;foreach($p['clips'] as $c){if(empty($c['export'])||!empty($c['dirty']))continue;$file=$dir.'/exports/'.identifier($c['export']['id']).'/clip.mp4';if(is_file($file)){$name=sprintf('%02d-%s.mp4',++$count,preg_replace('/[^a-zA-Z0-9_-]/','_',substr($c['title'],0,60)));$zip->addFile($file,$name);$zip->setCompressionName($name,ZipArchive::CM_STORE);}}$zip->close();if(!$count)throw new RuntimeException('Render a clip first.');return $path;}

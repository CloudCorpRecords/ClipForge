<?php
require_once __DIR__.'/social.php';
function studioHealth(string $csrf):array {$c=config();return ['ok'=>true,'csrf'=>$csrf,'key_set'=>!empty($c['openrouter_key']),'model'=>$c['model']??'google/gemini-2.5-flash','stt_model'=>$c['stt_model']??'openai/whisper-1','brand'=>$c['brand']??['font'=>'Arial','color'=>'#FFFFFF','highlight'=>'#C8ED48','style'=>'pop'],'links'=>$c['links']??['site'=>'','course'=>''],'profile'=>readStore('profile.json'),'ghl'=>socialPublic()];}
function studioApi(string $path,array $body,string $method,string $csrf):mixed {
 $parts=parse_url($path);parse_str($parts['query']??'',$query);$route=$parts['path']??'';$segments=explode('/',trim($route,'/'));
 $readOnly=$route==='/health'||$route==='/projects'||$route==='/saved'||$route==='/jobs'||preg_match('~^/projects/[a-f0-9]{24}$~',$route)||preg_match('~^/ghl/(accounts|users|posts)(/[A-Za-z0-9_-]+)?$~',$route)||$route==='/folders';
 if($method==='GET'&&!$readOnly){http_response_code(405);throw new RuntimeException('This action requires a protected write request.');}
 if($route==='/health')return studioHealth($csrf);
 if($route==='/settings'){
  $c=config();foreach(['key'=>'openrouter_key','model'=>'model','stt_model'=>'stt_model','ghl_token'=>'ghl_token','ghl_location'=>'ghl_location','ghl_user'=>'ghl_user','ghl_accounts'=>'ghl_accounts'] as $from=>$to)if(array_key_exists($from,$body))$c[$to]=$body[$from];
  $c['brand']??=[];foreach(['caption_font'=>'font','caption_color'=>'color','caption_highlight'=>'highlight','caption_style'=>'style'] as $from=>$to)if(isset($body[$from]))$c['brand'][$to]=$body[$from];
  foreach(['site_url'=>'site','course_url'=>'course'] as $from=>$to)if(isset($body[$from]))$c['links'][$to]=substr($body[$from],0,2000);
  if(isset($body['profile'])){if(!is_array($body['profile']))throw new RuntimeException('Invalid creator profile.');store('profile.json',array_map(fn($v)=>substr((string)$v,0,6000),$body['profile']));}store('config.json',$c);return studioHealth($csrf);
 }
 if($route==='/folders'&&$method==='GET')return readStore('folders.json');
 if($segments[0]==='folders'){
  $folders=readStore('folders.json');$fid=$segments[1]??id();identifier($fid);$existing=null;foreach($folders as $f)if($f['id']===$fid)$existing=$f;
  if(($segments[2]??'')==='channel-videos'){
   if(!$existing||empty($existing['channel_url']))throw new RuntimeException('Add a channel URL in folder settings.');
   if(!empty($existing['channel_cache'])&&($existing['channel_checked']??0)>time()-900)return $existing['channel_cache'];
   $videos=smallPrediction(['task'=>'channel','video_url'=>$existing['channel_url']])['videos']??[];
   foreach($folders as &$f)if($f['id']===$fid){$f['channel_cache']=$videos;$f['channel_checked']=time();}unset($f);store('folders.json',$folders);return $videos;
  }
  $folders=array_values(array_filter($folders,fn($f)=>$f['id']!==$fid));
  if($method==='DELETE'){foreach(glob(PRIVATE_DIR.'/project-*.json') as $file){$p=json_decode(file_get_contents($file),true);if(($p['folder_id']??'')===$fid){$p['folder_id']=null;saveProject($p);}}store('folders.json',$folders);return ['ok'=>true];}
  $name=trim($body['name']??'');if(!$name)throw new RuntimeException('Give your folder a name.');$f=['id'=>$fid,'name'=>substr($name,0,120),'instructions'=>substr($body['instructions']??'',0,6000),'channel_url'=>substr($body['channel_url']??'',0,500)];$folders[]=$f;store('folders.json',$folders);return $f;
 }
 if($route==='/projects'||$route==='/saved'){
  $all=[];$saved=[];foreach(glob(PRIVATE_DIR.'/project-*.json') as $file){$p=json_decode(file_get_contents($file),true);if(!empty($p['deleted']))continue;$p=studioProject($p);$all[]=$p;foreach($p['clips'] as $c)if(!empty($c['saved']))$saved[]=['project_id'=>$p['id'],'project'=>$p['title'],'title'=>$c['title'],'export_id'=>$c['export']['id']??null,'ghl'=>!empty($c['ghl']['url'])];}usort($all,fn($a,$b)=>$b['created']<=>$a['created']);return $route==='/saved'?['clips'=>$saved]:$all;
 }
 if($route==='/jobs'){
  $jobs=[];foreach(glob(PRIVATE_DIR.'/project-*.json') as $file){$p=json_decode(file_get_contents($file),true);if(!empty($p['deleted'])||empty($p['job'])&&empty($p['prediction']))continue;try{$p=syncProject($p['id']);}catch(Throwable $e){$p=project($p['id']);$p['error']='Waiting to save cloud files: '.$e->getMessage();}$jobs[]=studioJob($p);}return $jobs;
 }
 if($segments[0]==='jobs'&&($segments[2]??'')==='cancel'){foreach(glob(PRIVATE_DIR.'/project-*.json') as $file){$p=json_decode(file_get_contents($file),true);if(($p['job']['id']??$p['prediction']??'')===($segments[1]??'')){replicate('POST','predictions/'.$p['prediction'].'/cancel',[]);return ['ok'=>true];}}throw new RuntimeException('Job not found.');}
 if($segments[0]==='trash'&&($segments[2]??'')==='restore'){$p=project($segments[1]);unset($p['deleted']);saveProject($p);return studioProject($p);}
 if($segments[0]==='import'){
  $values=$_POST?:$body;$input=['task'=>'import'];$source=$values['url']??'';
  if($segments[1]==='upload'){$file=$_FILES['file']??null;if(!$file||$file['error']!==UPLOAD_ERR_OK)throw new RuntimeException('Upload failed. Check the PHP upload limit.');if($file['size']>500*1024**2)throw new RuntimeException('Uploads are limited to 500 MB. Use a direct URL for a larger video.');$input['video']=uploadReplicate($file['tmp_name']);}else{if(!$source)throw new RuntimeException('Add a video link.');$input['video_url']=$source;}
  $p=['id'=>id(),'title'=>'Importing video…','source'=>$source,'created'=>time(),'folder_id'=>$values['folder_id']??null,'status'=>'ready','clips'=>[]];$job=studioStart($p,$input,'import');return ['project'=>studioProject(project($p['id'])),'job'=>$job];
 }
 if($segments[0]==='ghl')return socialApi($segments,$query,$body,$method);
 if($segments[0]!=='projects'||empty($segments[1]))throw new RuntimeException('Unknown studio action.');
 $pid=identifier($segments[1]);$p=project($pid);if(!empty($p['deleted']))throw new RuntimeException('This video is in the trash.');$dir=PRIVATE_DIR.'/assets/'.$pid;$action=$segments[2]??'';
 if(!$action){
  if($method==='GET')return studioProject($p);studioIdle($p);
  if($method==='DELETE'){$p['deleted']=true;saveProject($p);return ['restore_id'=>$pid];}
  if(isset($body['title'])){$title=trim($body['title']);if(!$title)throw new RuntimeException('Give the video a title.');$p['title']=$p['custom_title']=substr($title,0,200);}
  if(array_key_exists('folder_id',$body))$p['folder_id']=$body['folder_id']?:null;saveProject($p);return studioProject($p);
 }
 studioIdle($p);
 if($action==='analyze'){
  $profile=studioProfile($p);$instructions=trim(json_encode($profile)."\n".($body['brief']??''));$selection=$body['selection']??'local';$transcription=$body['transcription']??'local';if(($selection==='openrouter'||$transcription==='openrouter')&&empty(config()['openrouter_key']))throw new RuntimeException('Add your OpenRouter key in AI & settings.');
  $input=['task'=>'analyze','video'=>uploadReplicate($dir.'/source.mp4'),'clip_count'=>max(1,min(12,(int)($body['count']??4))),'clip_length'=>max(10,min(90,(int)($body['length']??45))),'local_model'=>$body['local_model']??'small','selection'=>$selection,'transcription'=>$transcription,'instructions'=>$instructions,'options_json'=>json_encode(array_merge(studioOptions(),$body)),'render_clips'=>!empty($body['auto_export'])];
  if(is_file($dir.'/transcript.json'))$input['transcript_file']=uploadReplicate($dir.'/transcript.json');
  if(isset($body['window_start'],$body['window_end'])){$input['window_start']=(float)$body['window_start'];$input['window_end']=(float)$body['window_end'];}
  return studioStart($p,$input,'analyze');
 }
 if($action==='transcript'){
  $words=$body['words']??[];if(!is_array($words)||count($words)>100000)throw new RuntimeException('Invalid transcript.');
  foreach($words as &$w){$a=(float)($w['start']??-1);$b=(float)($w['end']??-1);if(!is_finite($a)||!is_finite($b)||$a<0||$a>=$b||$b>$p['meta']['duration']+.1)throw new RuntimeException('Invalid word timestamps.');$w=['start'=>$a,'end'=>$b,'word'=>substr(trim((string)($w['word']??'')),0,200)];}unset($w);usort($words,fn($a,$b)=>$a['start']<=>$b['start']);
  $t=is_file($dir.'/transcript.json')?json_decode(file_get_contents($dir.'/transcript.json'),true):[];$t['words']=$words;$t['segments']=[];$group=[];foreach($words as $w){$group[]=$w;if(count($group)>=10||preg_match('/[.!?]$/',$w['word'])){$t['segments'][]=['start'=>$group[0]['start'],'end'=>$w['end'],'text'=>implode(' ',array_column($group,'word'))];$group=[];}}if($group)$t['segments'][]=['start'=>$group[0]['start'],'end'=>end($group)['end'],'text'=>implode(' ',array_column($group,'word'))];file_put_contents($dir.'/transcript.json',json_encode($t),LOCK_EX);foreach($p['clips'] as &$c){$c['dirty']=true;unset($c['social']);}unset($c);saveProject($p);return ['ok'=>true];
 }
 if($action==='publish')return socialBatch($p,$body);
 if($action==='export'){$clips=array_values(array_filter($p['clips'],fn($c)=>empty($c['export'])||!empty($c['dirty'])));if(!$clips)return studioDone($p,'render','All clips are already rendered.');return studioRender($p,$clips);}
 if($action!=='clips')throw new RuntimeException('Unknown project action.');
 $cid=$segments[3]??null;
 if(!$cid){$c=studioClip($body,(float)$p['meta']['duration']);$p['clips'][]=$c;saveProject($p);return $c;}
 $index=null;foreach($p['clips'] as $i=>$c)if($c['id']===$cid){$index=$i;break;}if($index===null)throw new RuntimeException('Clip not found.');$c=$p['clips'][$index];$sub=$segments[4]??'';
 if(!$sub){$allowed=array_flip(['title','start','end','aspect','framing','focus_x','keyframes','resolution','auto_zoom','remove_silence','captions','caption_style','caption_font','caption_color','caption_highlight']);$c=studioClip(array_merge($c,array_intersect_key($body,$allowed),['id'=>$cid,'dirty'=>true]),(float)$p['meta']['duration']);unset($c['social']);$p['clips'][$index]=$c;saveProject($p);return $c;}
 if($sub==='export')return studioRender($p,[$c]);
 if($sub==='copy'){$profile=studioProfile($p);$spoken=studioSpoken($p,$c);$result=smallPrediction(['task'=>'copy','options_json'=>json_encode(array_merge(studioOptions(),['title'=>$c['title'],'spoken'=>$spoken,'profile'=>$profile,'links'=>config()['links']??[]]))]);$p['clips'][$index]['social']=$result['social'];saveProject($p);return $result['social'];}
 if($sub==='save'){if(empty($c['export'])||!empty($c['dirty']))throw new RuntimeException('Render this clip before saving.');if(socialPublic()['connected'])$c=socialMedia($p,$c);$c['saved']=true;$p['clips'][$index]=$c;return studioDone($p,'save');}
 if($sub==='publish'){socialPublish($p,$index,$body);return studioDone(project($pid),'publish','Post saved to Social Planner.');}
 throw new RuntimeException('Unknown clip action.');
}
function studioRender(array $p,array $clips):array {
 if(count($clips)>12)throw new RuntimeException('Render up to 12 clips at a time.');$dir=PRIVATE_DIR.'/assets/'.$p['id'];
 if(!is_file($dir.'/transcript.json'))file_put_contents($dir.'/transcript.json','{"words":[],"segments":[]}');
 return studioStart($p,['task'=>'render','video'=>uploadReplicate($dir.'/source.mp4'),'transcript_file'=>uploadReplicate($dir.'/transcript.json'),'edits_json'=>json_encode($clips)],'render',['clip_ids'=>array_column($clips,'id')]);
}
function studioSpoken(array $p,array $c):string {$path=PRIVATE_DIR.'/assets/'.$p['id'].'/transcript.json';$t=is_file($path)?json_decode(file_get_contents($path),true):[];return implode(' ',array_column(array_filter($t['words']??[],fn($w)=>$w['start']>=$c['start']&&$w['start']<$c['end']),'word'));}

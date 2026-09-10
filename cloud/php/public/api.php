<?php
declare(strict_types=1);
require dirname(__DIR__).'/lib.php';
session_start();header('Content-Type: application/json');header('Cache-Control: no-store');
$local=getenv('CLIPFORGE_DEV')==='1'&&in_array($_SERVER['REMOTE_ADDR']??'', ['127.0.0.1','::1'],true);
$action=$_GET['action']??'state';
try{
 $body=json_decode(file_get_contents('php://input'),true)??[];
 if($action==='login'){
  $password=config()['password']??'';
  if(!$password||!password_verify($body['password']??'',$password)){http_response_code(401);throw new RuntimeException('Incorrect website password.');}
  session_regenerate_id(true);$_SESSION['authenticated']=true;
 }
 if(!$local&&empty($_SESSION['authenticated'])){http_response_code(401);throw new RuntimeException('Sign in to your studio.');}
 $_SESSION['csrf']??=bin2hex(random_bytes(24));$csrf=$_SESSION['csrf'];
 if($_SERVER['REQUEST_METHOD']!=='GET'&&$action!=='login'&&!hash_equals($csrf,$_SERVER['HTTP_X_CSRF_TOKEN']??'')){http_response_code(403);throw new RuntimeException('Refresh the page before trying again.');}
 session_write_close();set_time_limit(0);
 $id=$_GET['id']??'';
 $mutationLock=null;
 if(in_array($_SERVER['REQUEST_METHOD'],['POST','PUT','DELETE'],true)&&$action!=='login'){$mutationLock=fopen(PRIVATE_DIR.'/mutations.lock','c');if(!flock($mutationLock,LOCK_EX|LOCK_NB))throw new RuntimeException('Another change is being saved. Try again shortly.');}
 if($action==='studio'){require dirname(__DIR__).'/studio_api.php';echo json_encode(studioApi($_GET['path']??'/health',$body,$_SERVER['REQUEST_METHOD'],$csrf),JSON_UNESCAPED_SLASHES);exit;}
 if($action==='login'){echo json_encode(['ok'=>true,'csrf'=>$csrf]);exit;}
 if($action==='state'){
  $projects=[];foreach(glob(PRIVATE_DIR.'/project-*.json') as $file){$p=json_decode(file_get_contents($file),true);if(empty($p['deleted']))$projects[]=publicProject($p);}
  usort($projects,fn($a,$b)=>$b['created']<=>$a['created']);
  $out=['projects'=>$projects,'folders'=>readStore('folders.json'),'profile'=>readStore('profile.json'),'csrf'=>$csrf,'configured'=>!empty(config()['replicate_token'])&&!empty(config()['deployment'])];
 }elseif($action==='folder'&&$_SERVER['REQUEST_METHOD']==='POST'){
  $folders=readStore('folders.json');$fid=$body['id']??id();identifier($fid);$name=trim($body['name']??'');if(!$name)throw new RuntimeException('Name your folder.');
  $item=['id'=>$fid,'name'=>substr($name,0,120),'instructions'=>substr($body['instructions']??'',0,6000)];$folders=array_values(array_filter($folders,fn($f)=>$f['id']!==$fid));if(empty($body['delete']))$folders[]=$item;else{foreach(glob(PRIVATE_DIR.'/project-*.json') as $file){$p=json_decode(file_get_contents($file),true);if(($p['folder_id']??'')===$fid){$p['folder_id']='';saveProject($p);}}}store('folders.json',$folders);$out=['ok'=>true];
 }elseif($action==='profile'&&$_SERVER['REQUEST_METHOD']==='POST'){store('profile.json',['instructions'=>substr($body['instructions']??'',0,6000)]);$out=['ok'=>true];
 }elseif($action==='import'&&$_SERVER['REQUEST_METHOD']==='POST'){
  $values=$_POST?:$body;$pid=id();$folder=$values['folder_id']??'';
  $instructions=readStore('profile.json')['instructions']??'';foreach(readStore('folders.json') as $f)if($f['id']===$folder)$instructions.="\n".$f['instructions'];
  $input=['task'=>'analyze','video_url'=>$values['url']??'','clip_count'=>max(1,min(6,(int)($values['count']??3))),'clip_length'=>max(10,min(90,(int)($values['length']??30))),'instructions'=>$instructions,'preview_seconds'=>!empty($values['preview'])?60:0,'render_clips'=>false];
  if(isset($_FILES['video'])){if($_FILES['video']['error']!==UPLOAD_ERR_OK)throw new RuntimeException('Upload failed; check PHP upload limits.');if($_FILES['video']['size']>500*1024**2)throw new RuntimeException('Website upload limit is 500 MB. Use a direct video URL for larger files.');$input['video']=uploadReplicate($_FILES['video']['tmp_name']);unset($input['video_url']);}
  if(empty($input['video'])&&empty($input['video_url']))throw new RuntimeException('Add a video URL or upload a file.');
  $job=startPrediction($input);$p=['id'=>$pid,'title'=>'Importing video…','folder_id'=>$folder,'created'=>time(),'status'=>$job['status'],'prediction'=>$job['id'],'clips'=>[]];saveProject($p);$out=publicProject($p);
 }elseif($action==='poll'){$out=publicProject(syncProject($id));
 }elseif($action==='project'){
  $p=project($id);
  if($_SERVER['REQUEST_METHOD']==='POST'){
   if(isset($body['title'])){$p['custom_title']=substr(trim($body['title']),0,200);$p['title']=$p['custom_title'];}
   if(isset($body['folder_id']))$p['folder_id']=$body['folder_id'];
   if(!empty($body['delete'])){if(!in_array($p['status'],['ready','failed','canceled']))throw new RuntimeException('Cancel the active job before deleting.');$p['deleted']=true;}
   saveProject($p);
  }
  $out=publicProject($p);$path=PRIVATE_DIR.'/assets/'.$id.'/transcript.json';if(is_file($path))$out['transcript']=json_decode(file_get_contents($path),true);
 }elseif($action==='render'&&$_SERVER['REQUEST_METHOD']==='POST'){
  $p=project($id);if($p['status']!=='ready')throw new RuntimeException('Wait for the current job.');$edits=$body['clips']??[];if(!is_array($edits)||!count($edits)||count($edits)>6)throw new RuntimeException('Choose 1–6 clips.');
  $dir=PRIVATE_DIR.'/assets/'.$id;
  $input=['task'=>'render','video'=>uploadReplicate($dir.'/source.mp4'),'transcript_file'=>uploadReplicate($dir.'/transcript.json'),'edits_json'=>json_encode($edits)];
  $job=startPrediction($input);$p['custom_title']=$p['title'];$p['prediction']=$job['id'];$p['status']=$job['status'];$p['clips']=$edits;saveProject($p);$out=publicProject($p);
 }elseif($action==='cancel'&&$_SERVER['REQUEST_METHOD']==='POST'){$p=project($id);replicate('POST','predictions/'.$p['prediction'].'/cancel',[]);$out=['ok'=>true];
 }else{http_response_code(404);throw new RuntimeException('Unknown action.');}
 echo json_encode($out,JSON_UNESCAPED_SLASHES);
}catch(Throwable $e){if(http_response_code()<400)http_response_code(400);echo json_encode(['error'=>$e->getMessage()]);}

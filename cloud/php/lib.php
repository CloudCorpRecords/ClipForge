<?php
declare(strict_types=1);
const PRIVATE_DIR=__DIR__.'/private';
function config():array {return is_file(PRIVATE_DIR.'/config.json') ? json_decode(file_get_contents(PRIVATE_DIR.'/config.json'),true,512,JSON_THROW_ON_ERROR) : [];}
function store(string $name,array $value):void {$path=PRIVATE_DIR.'/'.$name; $temp=$path.'.'.bin2hex(random_bytes(5)).'.tmp';file_put_contents($temp,json_encode($value,JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES),LOCK_EX);chmod($temp,0600);rename($temp,$path);}
function readStore(string $name,array $default=[]):array {$p=PRIVATE_DIR.'/'.$name;return is_file($p)?json_decode(file_get_contents($p),true,512,JSON_THROW_ON_ERROR):$default;}
function identifier(string $id):string {if(!preg_match('/^[a-f0-9]{24}$/',$id))throw new RuntimeException('Invalid project ID.');return $id;}
function id():string {return bin2hex(random_bytes(12));}
function project(string $id):array {$p=readStore('project-'.identifier($id).'.json');if(!$p)throw new RuntimeException('Project not found.');return $p;}
function saveProject(array $p):void {store('project-'.identifier($p['id']).'.json',$p);}
function replicate(string $method,string $path,?array $body=null):array {
 $token=config()['replicate_token']??'';if(!$token)throw new RuntimeException('Add your Replicate API token in server configuration.');
 $h=curl_init('https://api.replicate.com/v1/'.$path);curl_setopt_array($h,[CURLOPT_RETURNTRANSFER=>true,CURLOPT_CUSTOMREQUEST=>$method,CURLOPT_HTTPHEADER=>['Authorization: Bearer '.$token,'Content-Type: application/json'],CURLOPT_TIMEOUT=>40]);if($body!==null)curl_setopt($h,CURLOPT_POSTFIELDS,json_encode($body));
 $raw=curl_exec($h);$status=curl_getinfo($h,CURLINFO_RESPONSE_CODE);if($raw===false)throw new RuntimeException('Replicate connection failed: '.curl_error($h));$out=json_decode($raw,true);
 if($status>=400)throw new RuntimeException('Replicate '.$status.': '.($out['detail']??$out['error']??'Request rejected'));return $out??[];
}
function uploadReplicate(string $file):string {
 if(!is_file($file)||!is_readable($file))throw new RuntimeException('The source file is unavailable. Import the video again.');
 for($attempt=0;$attempt<3;$attempt++){
  $h=curl_init('https://api.replicate.com/v1/files');curl_setopt_array($h,[CURLOPT_RETURNTRANSFER=>true,CURLOPT_POST=>true,CURLOPT_HTTP_VERSION=>CURL_HTTP_VERSION_1_1,CURLOPT_HTTPHEADER=>['Authorization: Bearer '.(config()['replicate_token']??'')],CURLOPT_POSTFIELDS=>['content'=>new CURLFile($file)],CURLOPT_TIMEOUT=>1200]);$raw=curl_exec($h);$code=curl_getinfo($h,CURLINFO_RESPONSE_CODE);$out=$raw===false?[]:json_decode($raw,true);
  if($code===201&&!empty($out['urls']['get']))return $out['urls']['get'];
  if($raw!==false&&$code<500&&$code!==429)break;
  if($attempt<2)sleep($attempt+1);
 }
 throw new RuntimeException('Replicate file upload failed (HTTP '.$code.'). Your saved video and edits are intact. Try rendering again.');
}
function saveRemote(string $url,string $path):void {
 if(str_starts_with($url,'data:')){
  $comma=strpos($url,',');if($comma===false||!preg_match('~^data:[a-zA-Z0-9.+/-]+;base64$~',substr($url,0,$comma)))throw new RuntimeException('Invalid embedded output.');
  if(strlen($url)>140*1024**2)throw new RuntimeException('Embedded output is too large; update the Cog runtime to use file delivery.');
  $h=fopen($path.'.part','wb');try{for($offset=$comma+1;$offset<strlen($url);$offset+=65536){$bytes=base64_decode(substr($url,$offset,65536),true);if($bytes===false)throw new RuntimeException('Invalid output encoding.');fwrite($h,$bytes);}}finally{fclose($h);}rename($path.'.part',$path);return;
 }

 $host=strtolower(parse_url($url,PHP_URL_HOST)??'');if(parse_url($url,PHP_URL_SCHEME)!=='https'||!($host==='replicate.delivery'||str_ends_with($host,'.replicate.delivery')||$host==='api.replicate.com'))throw new RuntimeException('Unexpected output file host.');
 $handle=fopen($path.'.part','wb');$h=curl_init($url);$bytes=0;
 curl_setopt_array($h,[CURLOPT_HTTPHEADER=>['Authorization: Bearer '.(config()['replicate_token']??'')],CURLOPT_TIMEOUT=>1200,CURLOPT_WRITEFUNCTION=>function($h,$chunk)use($handle,&$bytes){$bytes+=strlen($chunk);if($bytes>2.5*1024**3)return 0;return fwrite($handle,$chunk);}]);
 $ok=curl_exec($h);$code=curl_getinfo($h,CURLINFO_RESPONSE_CODE);fclose($handle);if(!$ok||$code!==200){@unlink($path.'.part');throw new RuntimeException('Could not preserve output file (HTTP '.$code.'). Retry before its one-hour expiry.');}rename($path.'.part',$path);
}
function startPrediction(array $input):array {
 $deployment=config()['deployment']??'';if(!preg_match('~^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$~',$deployment))throw new RuntimeException('Configure your Replicate deployment first.');
 if(!empty(config()['openrouter_key']))$input['openrouter_api_key']=config()['openrouter_key'];
 return replicate('POST','deployments/'.$deployment.'/predictions',['input'=>$input]);
}
function syncProject(string $id):array {return cloudSync($id);}
function publicProject(array $p):array {
 $stage='';foreach(explode("\n",$p['logs']??'') as $line)if(preg_match('/^(Importing video|Imported [0-9]+ MB|Transcribing [0-9]+|Transcript complete:|Preparing clip edits|Rendering clip|Cutting and tightening|Processing complete;)/',$line))$stage=substr($line,0,180);
 $p['stage']=$stage;unset($p['prediction'],$p['logs']);return $p;
}

require_once __DIR__.'/studio_core.php';

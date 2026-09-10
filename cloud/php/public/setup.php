<?php
declare(strict_types=1);
if (getenv('CLIPFORGE_SETUP')!=='1' || !in_array($_SERVER['REMOTE_ADDR'] ?? '', ['127.0.0.1','::1'],true)) {http_response_code(403);exit('Local setup only. Configure private/config.json on your server.');}
session_start();
$_SESSION['setup_csrf'] ??= bin2hex(random_bytes(24));
if ($_SERVER['REQUEST_METHOD']==='POST') {
 if(!hash_equals($_SESSION['setup_csrf'],$_POST['csrf']??'')){http_response_code(403);exit;}
 $p=dirname(__DIR__).'/private/config.json';$c=is_file($p)?json_decode(file_get_contents($p),true):[];
 foreach(['replicate_token','registry_token','deployment','openrouter_key','password'] as $key)if(!empty($_POST[$key]))$c[$key]=$key==='password'?password_hash($_POST[$key],PASSWORD_DEFAULT):trim($_POST[$key]);
 file_put_contents($p,json_encode($c,JSON_PRETTY_PRINT),LOCK_EX);chmod($p,0600);echo '<p>Configuration saved securely.</p>';
}
?>
<!doctype html><html><head><title>ClipForge Cloud setup</title></head><body><h1>ClipForge Cloud setup</h1><form method="post"><input type="hidden" name="csrf" value="<?=htmlspecialchars($_SESSION['setup_csrf'])?>"><label>Replicate API token<input name="replicate_token" type="password" autocomplete="off"></label><br><label>Registry login token<input name="registry_token" type="password" autocomplete="off"></label><br><label>Deployment<input name="deployment" value="myaiteam2/clipforge-engine"></label><br><label>Optional OpenRouter key<input name="openrouter_key" type="password" autocomplete="off"></label><br><label>Website password<input name="password" type="password" autocomplete="new-password"></label><br><button>Save configuration</button></form></body></html>

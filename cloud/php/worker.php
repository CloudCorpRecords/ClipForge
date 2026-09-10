<?php
require __DIR__.'/lib.php';
foreach(glob(PRIVATE_DIR.'/project-*.json') as $file){$p=json_decode(file_get_contents($file),true);if(!empty($p['deleted'])||in_array($p['status'],['ready','failed','canceled']))continue;try{syncProject($p['id']);}catch(Throwable $e){fwrite(STDERR,$p['id'].': '.$e->getMessage()."\n");}}

#!/usr/bin/env python3
"""Publish the Cog worker and configure the least-expensive Replicate deployment."""
import argparse,json,os,re,subprocess,sys,tempfile,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CONFIG=ROOT/'php/private/config.json'
COG=os.environ.get('COG_BIN','cog')
def request(method,path,body=None):
 req=urllib.request.Request('https://api.replicate.com/v1/'+path,data=json.dumps(body).encode() if body is not None else None,method=method,headers={'Authorization':'Bearer '+TOKEN,'Content-Type':'application/json','User-Agent':'ClipForge/1.0'})
 try:
  with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
 except urllib.error.HTTPError as e:
  if e.code==404:return None
  raise RuntimeError(f'Replicate returned HTTP {e.code}: {e.read().decode()[:500]}') from None
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--owner',required=True);parser.add_argument('--model',default='clipforge-engine');parser.add_argument('--deployment',default='clipforge-engine');parser.add_argument('--skip-push',action='store_true');parser.add_argument('--native-push',action='store_true',help='Use crane on the host to avoid VM upload problems');args=parser.parse_args()
 for value in [args.owner,args.model,args.deployment]:
  if not re.fullmatch('[a-z0-9_-]+',value):parser.error('Names may contain lowercase letters, numbers, underscores and hyphens.')
 config=json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
 TOKEN=os.environ.get('REPLICATE_API_TOKEN') or config.get('replicate_token')
 if not TOKEN:sys.exit('Set your Replicate token in private/config.json or REPLICATE_API_TOKEN.')
 account=request('GET','account');print('Authenticated:',account.get('username'))
 model=args.owner+'/'+args.model;deployment=args.owner+'/'+args.deployment
 existing=request('GET','models/'+model)
 if not existing:
  request('POST','models',{'owner':args.owner,'name':args.model,'visibility':'private','hardware':'cpu','description':'ClipForge CPU video import, word timestamps and captioned clips.'})
 if not args.skip_push:
  if config.get('registry_token'):subprocess.run([COG,'login','--token-stdin'],input=config['registry_token']+'\n',text=True,check=True)
  version_text=subprocess.check_output([COG,'--version'],text=True)
  if '0.16.12' not in version_text:sys.exit('Use Cog 0.16.12 for this verified model. Set COG_BIN to its executable.')
  if args.native_push:
   subprocess.run([COG,'build','-t','r8.im/'+model,'--use-cog-base-image=false'],cwd=ROOT/'model',check=True)
   with tempfile.TemporaryDirectory(prefix='clipforge-publish-') as tmp:
    image=Path(tmp)/'image.tar'
    subprocess.run(['docker','save','r8.im/'+model,'-o',str(image)],check=True)
    upload_env=os.environ.copy();upload_env['GODEBUG']='http2client=0'
    subprocess.run(['crane','push',str(image),'r8.im/'+model],check=True,env=upload_env)
  else:subprocess.run([COG,'push','r8.im/'+model,'--use-cog-base-image=false'],cwd=ROOT/'model',check=True)
 version=None
 for _ in range(30):
  info=request('GET','models/'+model);version=(info.get('latest_version') or {}).get('id')
  if version:break
  time.sleep(2)
 if not version:sys.exit('Model push has no available version yet. Retry with --skip-push after it appears.')
 body={'model':model,'version':version,'hardware':'cpu','min_instances':0,'max_instances':1}
 old=request('GET','deployments/'+deployment)
 result=request('PATCH','deployments/'+deployment,{k:v for k,v in body.items() if k!='model'}) if old else request('POST','deployments',{'name':args.deployment,**body})
 config['deployment']=deployment;config['replicate_token']=TOKEN;CONFIG.parent.mkdir(exist_ok=True);CONFIG.write_text(json.dumps(config,indent=2));CONFIG.chmod(0o600)
 (ROOT/'deployment.json').write_text(json.dumps({'model':model,'version':version,'deployment':deployment,'hardware':'cpu','min_instances':0,'max_instances':1},indent=2))
 print('Deployment configured: https://replicate.com/deployments/'+deployment)
 print('PHP configuration updated. Run a real import to verify startup and predictions.')

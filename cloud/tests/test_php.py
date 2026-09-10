"""Exercise real PHP HTTP routes against an isolated temporary studio (no paid calls)."""
import http.cookiejar,json,os,shutil,socket,subprocess,tempfile,time,unittest,urllib.request,urllib.error
from pathlib import Path
class Website(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
  shutil.copytree(Path(__file__).resolve().parents[1]/'php',cls.root/'php',ignore=shutil.ignore_patterns('private'))
  private=cls.root/'php/private';private.mkdir()
  hashed=subprocess.check_output(['php','-r',"echo password_hash('test-studio-password', PASSWORD_DEFAULT);"]).decode()
  (private/'config.json').write_text(json.dumps({'password':hashed,'replicate_token':'test-private-token'}))
  cls.pid='a'*24
  (private/f'project-{cls.pid}.json').write_text(json.dumps({'id':cls.pid,'title':'Test video','created':1,'status':'ready','clips':[]}))
  assets=private/'assets'/cls.pid;assets.mkdir(parents=True);(assets/'source.mp4').write_bytes(b'0123456789')
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  cls.url=f'http://127.0.0.1:{port}/';cls.http=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
  cls.server=subprocess.Popen(['php','-S',f'127.0.0.1:{port}','-t',str(cls.root/'php/public')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env={**os.environ,'CLIPFORGE_DEV':'0','CLIPFORGE_SETUP':'0'})
  for _ in range(50):
   try:urllib.request.urlopen(cls.url);break
   except OSError:time.sleep(.05)
 @classmethod
 def tearDownClass(cls):cls.server.terminate();cls.server.wait();cls.temp.cleanup()
 def request(self,path,body=None,headers=None):
  req=urllib.request.Request(self.url+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json',**(headers or {})})
  try:r=self.http.open(req)
  except urllib.error.HTTPError as e:r=e
  return r.status,r.read(),r.headers
 def test_embedded_output_fallback(self):
  lib=str(self.root/'php/lib.php');target=str(self.root/'recovered.mp4')
  code='require '+json.dumps(lib)+'; saveRemote("data:video/mp4;base64,dmlkZW8=",'+json.dumps(target)+');'
  subprocess.run(['php','-r',code],check=True)
  self.assertEqual(Path(target).read_bytes(),b'video')
 def test_workflow(self):
  status,_,_=self.request('api.php');self.assertEqual(status,401)
  status,body,_=self.request('api.php?action=login',{'password':'test-studio-password'});self.assertEqual(status,200);csrf=json.loads(body)['csrf'];headers={'X-CSRF-Token':csrf}
  status,body,_=self.request('api.php');self.assertEqual(status,200);self.assertNotIn(b'test-private-token',body)
  status,_,_=self.request('api.php?action=folder',{'name':'My channel'});self.assertEqual(status,403)
  self.assertEqual(self.request('api.php?action=folder',{'name':'My channel','instructions':'Teach simply'},headers)[0],200)
  folder=json.loads(self.request('api.php')[1])['folders'][0]
  self.assertEqual(self.request('api.php?action=project&id='+self.pid,{'title':'Renamed','folder_id':folder['id']},headers)[0],200)
  self.assertEqual(self.request('api.php?action=folder',{**folder,'delete':True},headers)[0],200)
  p=json.loads(self.request('api.php?action=project&id='+self.pid)[1]);self.assertEqual(p['folder_id'],'');self.assertEqual(p['title'],'Renamed')
  status,body,h=self.request('asset.php?id='+self.pid+'&file=source.mp4',headers={'Range':'bytes=2-5'});self.assertEqual((status,body),(206,b'2345'));self.assertEqual(h['Content-Range'],'bytes 2-5/10')
  self.assertEqual(self.request('asset.php?id='+self.pid+'&file=../../config.json')[0],404)
  self.assertNotIn(b'test-private-token',self.request('private/config.json')[1])
  self.assertEqual(self.request('setup.php')[0],403)
  status,body,_=self.request('api.php?action=studio&path=%2Fhealth');self.assertEqual(status,200);self.assertNotIn(b'test-private-token',body)
  status,body,_=self.request('api.php?action=studio&path=%2Fprojects%2F'+self.pid);self.assertEqual(json.loads(body)['title'],'Renamed')
  # Exercise the original studio's manual-clip and keyframe persistence contract.
  raw={'title':'Manual moment','start':1,'end':8,'keyframes':[{'time':0,'x':.5,'y':.5,'zoom':1.1}]}
  pf=self.root/'php/private'/f'project-{self.pid}.json';saved=json.loads(pf.read_text());saved['meta']={'duration':10,'width':640,'height':360};pf.write_text(json.dumps(saved))
  status,body,_=self.request('api.php?action=studio&path=%2Fprojects%2F'+self.pid+'%2Fclips',raw,headers);self.assertEqual(status,200);clip=json.loads(body);self.assertEqual(clip['keyframes'][0]['zoom'],1.1)
  self.assertEqual(self.request('api.php?action=studio&path=%2Fprojects%2F'+self.pid+'%2Fclips',{**raw,'end':20},headers)[0],400)

  self.assertEqual(self.request('api.php?action=project&id='+self.pid,{'delete':True},headers)[0],200)
  self.assertEqual(json.loads(self.request('api.php')[1])['projects'],[])
  self.assertEqual(self.request('asset.php?id='+self.pid+'&file=source.mp4')[0],404)
if __name__=='__main__':unittest.main()

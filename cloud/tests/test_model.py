"""Pure validation checks, run inside the Cog image without loading Whisper."""
import math,unittest
from unittest.mock import patch
from predict import validate_edit,public_url
class ModelValidation(unittest.TestCase):
 def test_ranges_and_canvas(self):
  for edit in [{'start':-1,'end':10},{'start':0,'end':181},{'start':0,'end':float('nan')},{'start':0,'end':10,'aspect':'bad'}]:
   with self.assertRaises(ValueError):validate_edit(edit,200)
 def test_keyframe_limits(self):
  valid={'start':10,'end':30,'keyframes':[{'time':5,'x':.4,'zoom':1.2},{'time':0}]}
  self.assertEqual(validate_edit(valid,60)['keyframes'][0]['time'],0)
  for points in [[{'time':21}],[{'x':float('nan')}],[{'zoom':3}],[{'time':0},{'time':0}]]:
   with self.assertRaises(ValueError):validate_edit({'start':10,'end':30,'keyframes':points},60)
 def test_private_urls(self):
  with patch('socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',80))]):
   with self.assertRaises(ValueError):public_url('http://localhost/video.mp4')
  with self.assertRaises(ValueError):public_url('file:///etc/passwd')
  with self.assertRaises(ValueError):public_url('https://user:password@example.com/video')
if __name__=='__main__':unittest.main()

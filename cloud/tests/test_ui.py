"""Guard the user's requirement to retain the Chrome studio's exact UI structure."""
import unittest
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[2]
class Structure(HTMLParser):
 def __init__(self):super().__init__();self.tags=[]
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if tag not in ('script',):self.tags.append((tag,attrs.get('id'),attrs.get('class')))
class OriginalUI(unittest.TestCase):
 def test_styles_are_identical(self):self.assertEqual((ROOT/'extension/studio/style.css').read_bytes(),(ROOT/'cloud/php/public/style.css').read_bytes())
 def test_dom_layout_and_controls_are_identical(self):
  original=Structure();original.feed((ROOT/'extension/studio/index.html').read_text());web=Structure();web.feed((ROOT/'cloud/php/public/index.php').read_text());self.assertEqual(original.tags,web.tags)
if __name__=='__main__':unittest.main()

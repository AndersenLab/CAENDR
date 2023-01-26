import os
import markdown
import requests

from caendr.services.logger import logger
from flask import Markup, render_template_string


MODULE_SITE_BUCKET_PUBLIC_NAME = os.environ.get('MODULE_SITE_BUCKET_PUBLIC_NAME')


def render_markdown(filename, directory="base/static/content/markdown"):
  path = os.path.join(directory, filename)
  if not os.path.exists(path):
    return ''
  with open(path) as f:
    template = render_template_string(f.read(), **locals())
    return Markup(markdown.markdown(template))


def render_ext_markdown(url: str):
  if url is None:
    return ''
  
  r = requests.get(url)
  if r.status_code == 200:
    template = render_template_string(r.text, **locals())
    return Markup(markdown.markdown(template))

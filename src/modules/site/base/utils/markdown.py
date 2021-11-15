import os
import markdown
from flask import Markup, render_template_string

def render_markdown(filename, directory="base/static/content/markdown"):
  path = os.path.join(directory, filename)
  if not os.path.exists(path):
    return ''
  with open(path) as f:
    template = render_template_string(f.read(), **locals())
    return Markup(markdown.markdown(template))

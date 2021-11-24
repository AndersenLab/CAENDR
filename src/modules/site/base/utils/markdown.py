import os
import markdown
from logzero import logger
from flask import Markup, render_template_string

from caendr.services.cloud.storage import get_blob

MODULE_SITE_BUCKET_PUBLIC_NAME = os.environ.get('MODULE_SITE_BUCKET_PUBLIC_NAME')


def render_markdown(filename, directory="base/static/content/markdown"):
  path = os.path.join(directory, filename)
  if not os.path.exists(path):
    return ''
  with open(path) as f:
    template = render_template_string(f.read(), **locals())
    return Markup(markdown.markdown(template))


def render_ext_markdown(bucket: str, path: str):
  blob = get_blob(bucket, path)
  if blob:
    md = str(blob.download_as_text(raw_download=True))
    template = render_template_string(md, **locals())
    return Markup(markdown.markdown(template))

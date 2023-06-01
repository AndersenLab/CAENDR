import os
import markdown
import requests

from caendr.services.logger import logger
from caendr.models.error import ExternalMarkdownRenderError
from flask import Markup, render_template_string


MODULE_SITE_BUCKET_PUBLIC_NAME = os.environ.get('MODULE_SITE_BUCKET_PUBLIC_NAME')


def render_markdown(filename, directory="base/static/content/markdown"):
  path = os.path.join(directory, filename)
  if not os.path.exists(path):
    return ''
  with open(path) as f:
    template = render_template_string(f.read(), **locals())
    return Markup(markdown.markdown(template))


def render_ext_markdown(url: str, ignore_err=False):
  if url is None:
    return ''

  template = ''

  # Wrap main logic in a try-except block so we can optionally handle errors here
  try:
    r = requests.get(url)
    if r.status_code == 200:

      # Render the template
      try:
        template = render_template_string(r.text, **locals())

      # If there was an error rendering the template, raise it
      except Exception as ex:
        raise ExternalMarkdownRenderError(url, ex) from ex

    # If there was an error with the request, raise it
    else:
      raise ExternalMarkdownRenderError(url, f'Bad request: {r}')

  # Optionally ignore the error (log it and return an empty string)
  except ExternalMarkdownRenderError as ex:
    if ignore_err:
      logger.error(ex)
    else:
      raise

  return Markup(markdown.markdown(template))

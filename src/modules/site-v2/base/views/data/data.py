import yaml

from flask import render_template, Blueprint
from extensions import cache
from config import config

from caendr.models.error import EnvVarError
from caendr.services.cloud.storage import get_blob


data_bp = Blueprint(
  'data', __name__, template_folder='templates'
)


#
# Landing Page
#
@data_bp.route('/')
@cache.memoize(60*60)
def data():
  disable_parent_breadcrumb = True
  return render_template('data/landing.html', **locals())


#
# Download Data
#
@data_bp.route('/download')
@cache.memoize(60*60)
def download():
  title = 'Download Data'
  disable_parent_breadcrumb = True
  return render_template('data/download.html', **locals())


#
# Protocols
#
@data_bp.route("/protocols")
@cache.memoize(60*60)
def protocols():

    # Get location of YAML file in GCP
    MODULE_SITE_BUCKET_ASSETS_NAME = config.get('MODULE_SITE_BUCKET_ASSETS_NAME')
    if not MODULE_SITE_BUCKET_ASSETS_NAME:
      raise EnvVarError('MODULE_SITE_BUCKET_ASSETS_NAME')

    # Download the YAML file as a string
    blob = get_blob(MODULE_SITE_BUCKET_ASSETS_NAME, 'protocols/protocols.yaml')
    content = blob.download_as_text()

    # Initialize params and render HTML page
    params = {
      'title': "Protocols",
      'disable_parent_breadcrumb': True,
      'protocols': yaml.safe_load(content),
    }
    return render_template('data/protocols.html', **params)


#
# Submit A Strain
#
@data_bp.route('/submit')
@cache.memoize(60*60)
def submit_strain():
  """
      Google form for submitting strains
  """
  title = "Submit A Strain"
  disable_parent_breadcrumb = True

  # TODO: Move this to configurable location
  #STRAIN_SUBMISSION_FORM = '1w0VjB3jvAZmQlDbxoTx_SKkRo2uJ6TcjjX-emaQnHlQ'
  #strain_submission_url = f'https://docs.google.com/forms/d/{STRAIN_SUBMISSION_FORM}/viewform?embedded=true'
  strain_submission_url = "https://docs.google.com/forms/d/1w0VjB3jvAZmQlDbxoTx_SKkRo2uJ6TcjjX-emaQnHlQ/viewform?embedded=true"
  return render_template('data/submit-strain.html', **locals())
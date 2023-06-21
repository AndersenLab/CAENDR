import yaml

from flask import render_template, Blueprint
from extensions import cache
from config import config

from caendr.models.datastore import SPECIES_LIST
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
  return render_template('data/landing.html', **{
    'disable_parent_breadcrumb': True,
    'species_list': SPECIES_LIST,
  })


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


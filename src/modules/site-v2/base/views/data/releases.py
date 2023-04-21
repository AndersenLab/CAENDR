import json
import requests
import os

from flask import (request,
                    jsonify,
                    make_response,
                    render_template,
                    Blueprint,
                    send_file,
                    url_for,
                    abort)
from caendr.services.logger import logger

from config import config
from extensions import cache
from base.forms import VBrowserForm
from base.utils.auth import jwt_required

from caendr.api.strain import query_strains
from caendr.api.isotype import get_isotypes
from caendr.models.datastore import DatasetRelease, Species
from caendr.models.sql import Strain, StrainAnnotatedVariant
from caendr.services.cloud.storage import generate_blob_url
from caendr.services.dataset_release import get_all_dataset_releases, get_release_path, get_browser_tracks_path, get_release_bucket, find_dataset_release
from caendr.models.error import NotFoundError


releases_bp = Blueprint(
  'data_releases', __name__, template_folder='templates'
)


def interpret_url_vars(species, release_version):
  species = Species.get(species.replace('-', '_'))

  releases = get_all_dataset_releases(order='-version')
  release  = find_dataset_release(releases, release_version)

  return species, releases, release


# ============= #
#   Data Page   #
# ============= #


@releases_bp.route('/data-release')
@cache.memoize(60*60)
def data_releases():
  '''
    Landing page for dataset releases.
  '''
  return render_template('data/landing.html', **{
    'title': "Data Releases",
    'alt_parent_breadcrumb': {"title": "Data", "url": url_for('data.data')},
  })


@releases_bp.route('/data-release/<string:species>/latest')
@releases_bp.route('/data-release/<string:species>/<string:release_version>')
@cache.memoize(60*60)
def data_release_list(species, release_version=None):
  """
    Default data page - lists available releases.
  """

  # Look up the species and release version
  try:
    species, RELEASES, RELEASE = interpret_url_vars(species, release_version)

  # If either could not be found, return an error page
  except NotFoundError:
    return abort(404)

  title = "Data Releases"
  alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.data')}

  if RELEASE.report_type == 'V2':
    return data_v02(species, RELEASE, RELEASES)
  elif RELEASE.report_type == 'V1':
    return data_v01(species, RELEASE, RELEASES)

  return render_template('data/releases.html', **locals())


@cache.memoize(60*60)
def data_v02(species, RELEASE, RELEASES):
  title = "Data Releases"
  alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.data')}
  release_version = RELEASE.version
  strain_listing = query_strains(release_version=release_version)

  release_bucket = get_release_bucket()
  release_path = get_release_path(release_version)
  browser_tracks_path = get_browser_tracks_path()
  browser_tracks_url = generate_blob_url(release_bucket, browser_tracks_path)

  files = RELEASE.get_report_data_urls_map()
  return render_template('data/releases.html', **locals())


@cache.memoize(60*60)
def data_v01(species, RELEASE, RELEASES):
  # Legacy releases (Pre 20200101)
  title = "Data Releases"
  alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.data')}
  release_version = RELEASE.version
  strain_listing = query_strains(release_version=release_version)

  release_bucket = get_release_bucket()
  release_path = get_release_path(release_version)
  browser_tracks_path = get_browser_tracks_path()
  site_bucket_public_name = config.get('MODULE_SITE_BUCKET_PUBLIC_NAME', 'NONE')
  
  files = RELEASE.get_report_data_urls_map()

  try:
    vcf_summary_url = files.get('vcf_summary_url')
    vcf_summary = requests.get(vcf_summary_url).json()
  except json.JSONDecodeError:
    vcf_summary = None

  return render_template('data/releases.html', **locals())


# ======================= #
#   Alignment Data Page   #
# ======================= #
@releases_bp.route('/data-release/<string:species>/latest/alignment')
@releases_bp.route('/data-release/<string:species>/<string:release_version>/alignment')
@cache.memoize(60*60)
def alignment_data(species, release_version=None):

  # Look up the species and release version
  try:
    species, RELEASES, RELEASE = interpret_url_vars(species, release_version)

  # If either could not be found, return an error page
  except NotFoundError:
    return abort(404)

  # Pre-2020 releases don't have data organized the same way
  if RELEASE.report_type == 'V1':
    return 
  
  # Post-2020 releases
  title = "Alignment Data"
  alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.data')}
  strain_listing = query_strains(release_version=release_version)
  '''
  DATASET_RELEASE, WORMBASE_VERSION = list(filter(lambda x: x[0] == release_version, RELEASES))[0]
  REPORTS = ["alignment"]
  '''
  return render_template('data/alignment.html', **locals())



# =========================== #
#   Strain Issues Data Page   #
# =========================== #
@releases_bp.route('/data-release/<string:species>/latest/strain_issues')
@releases_bp.route('/data-release/<string:species>/<string:release_version>/strain_issues')
@cache.memoize(60*60)
def strain_issues(species, release_version=None):
  """
      Strain Issues page
  """

  # Look up the species and release version
  try:
    species, RELEASES, RELEASE = interpret_url_vars(species, release_version)

  # If either could not be found, return an error page
  except NotFoundError:
    return abort(404)

  # Pre-2020 releases don't have data organized the same way
  if RELEASE.report_type == 'V1':
    return 
  
  # Post-2020 releases
  title = "Strain Issues"
  alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.data')}
  strain_listing_issues = query_strains(release_version=release_version, issues=True)

  return render_template('strain/issues.html', **locals())

import json
import requests
import os

from flask import (request,
                    jsonify,
                    make_response,
                    render_template,
                    redirect,
                    Blueprint,
                    send_file,
                    url_for,
                    flash,
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
from caendr.services.cloud.storage import BlobURISchema, generate_blob_uri
from caendr.services.dataset_release import get_all_dataset_releases, get_browser_tracks_path, get_release_bucket, find_dataset_release
from caendr.utils.env import get_env_var
from caendr.utils.views import parse_species_and_release


BAM_BAI_DOWNLOAD_SCRIPT_NAME = get_env_var('BAM_BAI_DOWNLOAD_SCRIPT_NAME', as_template=True)


releases_bp = Blueprint(
  'data_releases', __name__, template_folder='templates'
)



# ============= #
#   Data Page   #
# ============= #


@releases_bp.route('')
@cache.memoize(60*60)
def data_releases():
  '''
    Landing page for dataset releases.
  '''
  return render_template('data/landing.html', **{
    'title': "Data Releases",
    'alt_parent_breadcrumb': {"title": "Data", "url": url_for('data.data')},
    'species_list': Species.all(),
  })


@releases_bp.route('/<string:species_name>/latest')
@releases_bp.route('/<string:species_name>/<string:release_version>')
@cache.memoize(60*60)
@parse_species_and_release
def data_release_list(species: Species, release: DatasetRelease):
  """
    Default data page - lists available releases.
  """

  # Package common params into an object
  params = {
    'species':  species,
    'RELEASE':  release,
    'RELEASES': get_all_dataset_releases(order='-version', species=species.name),
    'release_bucket': get_release_bucket(),
    'release_path': release.get_versioned_path_template().get_string(SPECIES = species.name),
    'fasta_path': release.get_fasta_filepath_url() if release.check_fasta_file_exists() else None,
    'fasta_name': release.get_fasta_filename(),
  }

  # Get list of files based on species
  try:
    files = release.get_report_data_urls_map(species.name)
  except Exception as ex:
    files = None
    logger.error(f'Failed to retrieve release files: {ex}')
    flash('Unable to retrieve release files at this time. Please try again later.', 'danger')

  # Update params object with version-specific fields
  if release.report_type == DatasetRelease.V2:
    params.update(data_v02(params, files))
  elif release.report_type == DatasetRelease.V1:
    params.update(data_v01(params, files))

  # Special case:
  # Only show the Divergent Regions BED file if it defines a valid track for this species + release,
  # even if the file exists.
  if files and 'Divergent Regions' not in release['browser_tracks']:
    files['divergent_regions_strain_bed']    = None
    files['divergent_regions_strain_bed_gz'] = None

  # Render the page
  return render_template('data/releases.html', **{
    'title': "Data Releases",
    'alt_parent_breadcrumb': {"title": "Data", "url": url_for('data.data')},

    'release_version': release.version,

    **params,
    'files': files,
  })


@cache.memoize(60*60)
def data_v02(params, files):
  '''
    Define additional parameters used by V2 releases.
  '''
  browser_tracks_path = get_browser_tracks_path().get_string_safe()
  return {
    'browser_tracks_path': browser_tracks_path,
    'browser_tracks_url': generate_blob_uri(params['release_bucket'], browser_tracks_path, schema=BlobURISchema.HTTPS),

    'download_bams_name': BAM_BAI_DOWNLOAD_SCRIPT_NAME.get_string(**{
      'SPECIES': params['species'].name,
      'RELEASE': params['RELEASE'].version,
    }),
  }


@cache.memoize(60*60)
def data_v01(params, files):
  '''
    Define additional parameters used by legacy V1 releases (pre 20200101).
  '''
  try:
    vcf_summary_url = files.get('vcf_summary_url')
    vcf_summary = requests.get(vcf_summary_url).json()
  except json.JSONDecodeError:
    vcf_summary = None

  return {
    'site_bucket_public_name': config.get('MODULE_SITE_BUCKET_PUBLIC_NAME', 'NONE'),
    'browser_tracks_path': get_browser_tracks_path().get_string_safe(),
    'vcf_summary_url': vcf_summary_url,
    'vcf_summary': vcf_summary,
  }


# ======================= #
#   Alignment Data Page   #
# ======================= #
@releases_bp.route('/<string:species_name>/latest/alignment')
@releases_bp.route('/<string:species_name>/<string:release_version>/alignment')
@cache.memoize(60*60)
@parse_species_and_release
def alignment_data(species: Species, release: DatasetRelease):

  # Pre-2020 releases don't have data organized the same way
  # TODO: Error page? Redirect to main release page?
  if release.report_type == DatasetRelease.V1:
    return

  # Post-2020 releases
  return render_template('data/alignment.html', **{
    'title': "Alignment Data",
    'subtitle': species.short_name,
    'alt_parent_breadcrumb': {"title": "Data", "url": url_for('data.data')},

    'species':  species,
    'RELEASE':  release,
    'RELEASES': get_all_dataset_releases(order='-version', species=species.name),

    'strain_listing': query_strains(release_version=release['version'], species=species.name),
  })
  # DATASET_RELEASE, WORMBASE_VERSION = list(filter(lambda x: x[0] == release_version, RELEASES))[0]
  # REPORTS = ["alignment"]



# =========================== #
#   Strain Issues Data Page   #
# =========================== #
@releases_bp.route('/<string:species_name>/latest/strain_issues')
@releases_bp.route('/<string:species_name>/<string:release_version>/strain_issues')
@cache.memoize(60*60)
@parse_species_and_release
def strain_issues(species: Species, release: DatasetRelease):
  """
    Strain Issues page
    Lists all strains with known issues for a given species & release.
  """

  # Pre-2020 releases don't have data organized the same way
  # TODO: Error page? Redirect to main release page?
  if release.report_type == DatasetRelease.V1:
    return

  # Post-2020 releases
  return render_template('strain/issues.html', **{
    'title': "Strain Issues",
    'subtitle': species.short_name,
    'alt_parent_breadcrumb': {"title": "Data", "url": url_for('data.data')},

    'species':  species,
    'RELEASE':  release,
    'RELEASES': get_all_dataset_releases(order='-version', species=species.name),

    'strain_listing_issues': query_strains(release_version=release['version'], species=species.name, issues=True),
  })

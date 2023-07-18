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
                    abort)
from caendr.services.logger import logger

from config import config
from extensions import cache
from base.forms import VBrowserForm
from base.utils.auth import jwt_required

from caendr.api.strain import query_strains
from caendr.api.isotype import get_isotypes
from caendr.models.datastore import DatasetRelease, Species, SPECIES_LIST
from caendr.models.sql import Strain, StrainAnnotatedVariant
from caendr.services.cloud.storage import generate_blob_url, check_blob_exists
from caendr.services.dataset_release import get_all_dataset_releases, get_browser_tracks_path, get_release_bucket, find_dataset_release
from caendr.models.error import NotFoundError, SpeciesUrlNameError
from caendr.utils.env import get_env_var


BAM_BAI_DOWNLOAD_SCRIPT_NAME = get_env_var('BAM_BAI_DOWNLOAD_SCRIPT_NAME', as_template=True)


releases_bp = Blueprint(
  'data_releases', __name__, template_folder='templates'
)


def interpret_url_vars(species_name, release_version):
  species = Species.get(species_name.replace('-', '_'))

  if species.get_url_name() != species_name:
    raise SpeciesUrlNameError(species.get_url_name())

  releases = get_all_dataset_releases(order='-version', species=species.name)
  release  = find_dataset_release(releases, release_version)

  return species, releases, release


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
    'species_list': SPECIES_LIST,
  })


@releases_bp.route('/<string:species>/latest')
@releases_bp.route('/<string:species>/<string:release_version>')
@cache.memoize(60*60)
def data_release_list(species, release_version=None):
  """
    Default data page - lists available releases.
  """

  # Look up the species and release version
  try:
    species, releases, release = interpret_url_vars(species, release_version)

  # If species name provided with underscore instead of dash, redirect to dashed version of URL
  except SpeciesUrlNameError as ex:
    return redirect(url_for('data_releases.data_release_list', species=ex.species_name, release_version=release_version))

  # If either could not be found, return an error page
  except NotFoundError:
    return abort(404)

  # Package common params into an object
  params = {
    'species':  species,
    'RELEASE':  release,
    'RELEASES': releases,
    'release_bucket': get_release_bucket(),
    'release_path': release.get_versioned_path_template().get_string(SPECIES = species.name),
    'fasta_path': release.get_fasta_filepath_url() if release.check_fasta_file_exists() else None,
    'fasta_name': release.get_fasta_filename(),
  }

  # Get list of files based on species
  files = release.get_report_data_urls_map(species.name)

  # Update params object with version-specific fields
  if release.report_type == DatasetRelease.V2:
    params.update(data_v02(params, files))
  elif release.report_type == DatasetRelease.V1:
    params.update(data_v01(params, files))

  # Special case:
  # Only show the Divergent Regions BED file if it defines a valid track for this species + release,
  # even if the file exists.
  if 'Divergent Regions' not in release['browser_tracks']:
    files['divergent_regions_strain_bed']    = None
    files['divergent_regions_strain_bed_gz'] = None

  # Render the page
  return render_template('data/releases.html', **{
    'title': "Data Releases",
    'alt_parent_breadcrumb': {"title": "Data", "url": url_for('data.data')},

    'release_version': release.version,
    'strain_listing': query_strains(release_version=release.version),

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
    'browser_tracks_url': generate_blob_url(params['release_bucket'], browser_tracks_path),

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
@releases_bp.route('/<string:species>/latest/alignment')
@releases_bp.route('/<string:species>/<string:release_version>/alignment')
@cache.memoize(60*60)
def alignment_data(species, release_version=None):

  # Look up the species and release version
  try:
    species, releases, release = interpret_url_vars(species, release_version)

  # If species name provided with underscore instead of dash, redirect to dashed version of URL
  except SpeciesUrlNameError as ex:
    return redirect(url_for('data_releases.alignment_data', species=ex.species_name, release_version=release_version))

  # If either could not be found, return an error page
  except NotFoundError:
    return abort(404)

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
    'RELEASES': releases,

    'strain_listing': query_strains(release_version=release_version, species=species.name),
  })
  # DATASET_RELEASE, WORMBASE_VERSION = list(filter(lambda x: x[0] == release_version, RELEASES))[0]
  # REPORTS = ["alignment"]



# =========================== #
#   Strain Issues Data Page   #
# =========================== #
@releases_bp.route('/<string:species>/latest/strain_issues')
@releases_bp.route('/<string:species>/<string:release_version>/strain_issues')
@cache.memoize(60*60)
def strain_issues(species, release_version=None):
  """
    Strain Issues page
    Lists all strains with known issues for a given species & release.
  """

  # Look up the species and release version
  try:
    species, releases, release = interpret_url_vars(species, release_version)

  # If species name provided with underscore instead of dash, redirect to dashed version of URL
  except SpeciesUrlNameError as ex:
    return redirect(url_for('data_releases.strain_issues', species=ex.species_name, release_version=release_version))

  # If either could not be found, return an error page
  except NotFoundError:
    return abort(404)

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
    'RELEASES': releases,

    'strain_listing_issues': query_strains(release_version=release_version, species=species.name, issues=True),
  })

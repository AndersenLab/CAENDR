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
from base.utils.view_decorators import parse_species_and_release

from caendr.api.strain import query_strains
from caendr.models.datastore import DatasetRelease, Species, TraitFile
from caendr.services.cloud.storage import BlobURISchema, generate_blob_uri
from caendr.services.cloud.aws_storage import AWSBlobURISchema, aws_generate_blob_uri
from caendr.services.dataset_release import get_all_dataset_releases, get_browser_tracks_path
from caendr.utils.env import get_env_var


BAM_BAI_DOWNLOAD_SCRIPT_NAME = get_env_var('BAM_BAI_DOWNLOAD_SCRIPT_NAME', as_template=True)
MODULE_DB_OPERATIONS_BUCKET_NAME = get_env_var('MODULE_DB_OPERATIONS_BUCKET_NAME', as_template=True)
DB_RELEASE_FILEPATH = get_env_var('MODULE_DB_OPERATIONS_RELEASE_FILEPATH', as_template=True)
GENE_GFF_FILENAME = get_env_var('GENE_GFF_FILENAME', as_template=True)
GENE_GTF_FILENAME = get_env_var('GENE_GTF_FILENAME', as_template=True)
GENE_IDS_FILENAME = get_env_var('GENE_IDS_FILENAME', as_template=True)

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
    'release_bucket': species['release_latest'],
    'release_path': release.get_versioned_path_template().get_string(SPECIES = species.name),
    'fasta_path': release.get_fasta_filepath(schema=AWSBlobURISchema.HTTPS) if release.check_fasta_file_exists() else None,
    'fasta_name': release.get_fasta_filename(),
    'gene_gff_path': generate_blob_uri(
      MODULE_DB_OPERATIONS_BUCKET_NAME.get_string(), 
      DB_RELEASE_FILEPATH.get_string(**{
        'SPECIES': species.name,
        'RELEASE': release.version,
        }),
        GENE_GFF_FILENAME.get_string(),
        schema=BlobURISchema.HTTPS),
    'gene_gff_name': GENE_GFF_FILENAME.get_string(),
    'gene_gtf_path': generate_blob_uri(
      MODULE_DB_OPERATIONS_BUCKET_NAME.get_string(), 
      DB_RELEASE_FILEPATH.get_string(**{
        'SPECIES': species.name,
        'RELEASE': release.version,
        }),
        GENE_GTF_FILENAME.get_string(),
        schema=BlobURISchema.HTTPS),
    'gene_gtf_name': GENE_GTF_FILENAME.get_string(),
    'gene_ids_path': generate_blob_uri(
      MODULE_DB_OPERATIONS_BUCKET_NAME.get_string(), 
      DB_RELEASE_FILEPATH.get_string(**{
        'SPECIES': species.name,
        'RELEASE': release.version,
        }),
        GENE_IDS_FILENAME.get_string(),
        schema=BlobURISchema.HTTPS),
    'gene_ids_name': GENE_IDS_FILENAME.get_string(),
  }

  # Get list of files based on species
  # try:
  files = release.get_report_data_urls_map(species.name)
  # except Exception as ex:
  #   files = None
  #   logger.error(f'Failed to retrieve release files: {ex}')
  #   flash('Unable to retrieve release files at this time. Please try again later.', 'danger')

  # Update params object with version-specific fields
  if release.report_type == DatasetRelease.V2:
    params.update(data_v02(params, files))
  elif release.report_type == DatasetRelease.V1:
    params.update(data_v01(params, files))
  params['current_release'] = get_all_dataset_releases(order='-version', species=species.name)[0].version

  # Special case:
  # Only show the Divergent Regions BED file if it defines a valid track for this species + release,
  # even if the file exists.
  if files and 'Hyper-divergent Regions' not in release['browser_tracks']:
    files['divergent_regions_strain_bed']    = None
    files['divergent_regions_strain_bed_gz'] = None

  # Check for downloadable trait files
  trait_files = [tf for tf in TraitFile.all().values() if tf.downloadable and tf.species.name == species.name]
  if files and len(trait_files) > 0:
    files['trait_files'] = trait_files

  if files and 'Isotype changelog' in files:
    r = requests.get(files['Isotype changelog'])
    if r.status_code == 200:
      parsed_changelog = [line.rstrip().split('\t') for line in r.text.split("\n")]
      files['Isotype changelog'] = {"header": parsed_changelog[0], "rows": parsed_changelog[1:]}

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
    'site_bucket_public_name': config.get('MODULE_SITE_BUCKET_DATASET_RELEASE_NAME', config.get('MODULE_SITE_BUCKET_PUBLIC_NAME_OVERRIDE', config.get('MODULE_SITE_BUCKET_PUBLIC_NAME', 'NONE'))),
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


# ======================= #
#   VCF Data Page   #
# ======================= #
@releases_bp.route('/<string:species_name>/latest/vcf')
@releases_bp.route('/<string:species_name>/<string:release_version>/vcf')
@cache.memoize(60*60)
@parse_species_and_release
def vcf_data(species: Species, release: DatasetRelease):

  # Pre-2020 releases don't have data organized the same way
  # TODO: Error page? Redirect to main release page?
  if release.report_type == DatasetRelease.V1:
    return

  # Post-2020 releases
  return render_template('data/vcf.html', **{
    'title': "VCF Data",
    'subtitle': species.short_name,
    'alt_parent_breadcrumb': {"title": "Data", "url": url_for('data.data')},

    'species':  species,
    'RELEASE':  release,
    'RELEASES': get_all_dataset_releases(order='-version', species=species.name),

    'strain_listing': query_strains(release_version=release['version'], species=species.name),
  })


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

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
from logzero import logger

from config import config
from extensions import cache
from base.forms import VBrowserForm
from base.utils.auth import jwt_required

from caendr.api.strain import query_strains
from caendr.api.isotype import get_isotypes
from caendr.models.datastore import DatasetRelease
from caendr.models.sql import Strain, StrainAnnotatedVariant
from caendr.services.cloud.storage import generate_blob_url
from caendr.services.dataset_release import get_dataset_release, get_all_dataset_releases, get_release_summary, get_release_path, get_browser_tracks_path, get_release_bucket
from caendr.models.error import NotFoundError


releases_bp = Blueprint('data_releases',
                        __name__,
                        template_folder='templates')


# ============= #
#   Data Page   #
# ============= #

@releases_bp.route('/release/latest')
@releases_bp.route('/release/<string:release_version>')
@cache.memoize(50)
def data(release_version=None):
  """ Default data page - lists available releases. """
  title = "Genomic Data"
  alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.landing')}
  RELEASES = get_all_dataset_releases(order='-version')
  
  # Get the requested release and throw an error if it doesn't exist
  RELEASE = None
  if release_version:
    for r in RELEASES:
      if r.version == release_version:
        RELEASE = r
        break
    if not RELEASE:
      raise NotFoundError(f'Release Version: {release_version} Not Found')
  else:
    RELEASE = RELEASES[0]
  
  if RELEASE.report_type == 'V2':
    return data_v02(RELEASE, RELEASES)
  elif RELEASE.report_type == 'V1':
    return data_v01(RELEASE, RELEASES)
  
  return render_template('data/releases.html', **locals())


@cache.memoize(50)
def data_v02(RELEASE, RELEASES):
  title = "Genomic Data"
  alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.landing')}
  release_version = RELEASE.version
  release_summary = get_release_summary(release_version)
  
  # TODO: REMOVE THESE STATIC VALUEs
  release_bucket = 'elegansvariation.org'
  browser_tracks_path = f'browser_tracks'
  release_path = f'releases/{release_version}'
  # TODO: restore these values
  # release_bucket = get_release_bucket()
  # release_path = get_release_path(release_version)
  # browser_tracks_path = get_browser_tracks_path()

  # TODO: move these paths to DatasetRelease file map
  release_notes_path = f'{release_path}/release_notes.md'
  release_methods_path = f'{release_path}/methods.md'
  release_data_url = generate_blob_url(release_bucket, release_path)
  browser_tracks_url = generate_blob_url(release_bucket, browser_tracks_path)

  divergent_regions_strain_bed_gz = f'{browser_tracks_url}/lee2020.divergent_regions_strain.bed.gz'
  alignment_report = f'{release_data_url}/alignment_report.html'
  gatk_report = f'{release_data_url}/gatk_report.html'
  concordance_report = f'{release_data_url}/concordance_report.html'

  # TODO: revert this to internal bucket
  f = RELEASE.get_report_data_urls_map(bucket_name='elegansvariation.org', blob_prefix='releases')
  return render_template('data/releases.html', **locals())


@cache.memoize(50)
def data_v01(RELEASE, RELEASES):
  # Legacy releases (Pre 20200101)
  title = "Genomic Data"
  alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.landing')}
  release_version = RELEASE.version
  release_summary = get_release_summary(release_version)
  
   
  # TODO: REMOVE THESE STATIC VALUEs
  release_bucket = 'elegansvariation.org'
  browser_tracks_path = f'browser_tracks'
  release_path = f'releases/{release_version}'
  # TODO: restore these values
  # release_bucket = get_release_bucket()
  # release_path = get_release_path(release_version)
  # browser_tracks_path = get_browser_tracks_path()
  release_data_url = generate_blob_url(release_bucket, release_path)
  
  # TODO: move these paths to DatasetRelease file map
  release_methods_path = f'{release_path}/methods.md'
  haplotype_png_url = f'{release_data_url}/haplotype/haplotype.png'
  haplotype_thumb_png_url = f'{release_data_url}/haplotype/haplotype.thumb.png'
  tajima_d_png_url = f'{release_data_url}/popgen/tajima_d.png'
  tajima_d_thumb_png_url = f'{release_data_url}/popgen/tajima_d.thumb.png'
  genome_svg_url = f'{release_data_url}/popgen/trees/genome.svg'
  
  # TODO: revert this to internal bucket
  f = RELEASE.get_report_data_urls_map(bucket_name='elegansvariation.org', blob_prefix='releases')
  phylo_url = f.get('phylo_url')
  vcf_summary_url = f.get('vcf_summary_url')

  try:
    vcf_summary = requests.get(vcf_summary_url).json()
  except json.JSONDecodeError:
    vcf_summary = None


  return render_template('data/releases.html', **locals())


# ======================= #
#   Alignment Data Page   #
# ======================= #
@releases_bp.route('/release/latest/alignment')
@releases_bp.route('/release/<string:release_version>/alignment')
@cache.memoize(50)
def alignment_data(release_version=''):
  pass

'''
@data_releases_bp.route('/release/latest/alignment')
@data_releases_bp.route('/release/<string:release_version>/alignment')
@cache.memoize(50)
def alignment_data(release_version=''):
  """
      Alignment data page
  """
  if release_version is None:
    release_version = config['DATASET_RELEASE']
  # Pre-2020 releases don't have data organized the same way
  if int(release_version) < 20200101:
      return 
  
  # Post-2020 releases
  title = "Alignment Data"
  alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.landing')}
  strain_listing = query_strains(release=release_version)
  RELEASES = config["RELEASES"]
  DATASET_RELEASE, WORMBASE_VERSION = list(filter(lambda x: x[0] == release_version, RELEASES))[0]
  REPORTS = ["alignment"]
  return render_template('alignment.html', **locals())'''

# =========================== #
#   Strain Issues Data Page   #
# =========================== #
@releases_bp.route('/release/latest/strain_issues')
@releases_bp.route('/release/<string:release_version>/strain_issues')
@cache.memoize(50)
def strain_issues(release_version=None):
    """
        Strain Issues page
    """
    RELEASES = get_all_dataset_releases(order='-version')
    
    # Get the requested release and throw an error if it doesn't exist
    RELEASE = None
    if release_version:
      for r in RELEASES:
        if r.version == release_version:
          RELEASE = r
          break
      if not RELEASE:
        raise NotFoundError(f'Release Version: {release_version} Not Found')
    else:
      RELEASE = RELEASES[0]

    # Pre-2020 releases don't have data organized the same way
    if int(release_version) < 20200101:
      return 
    
    # Post-2020 releases
    title = "Strain Issues"
    alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.landing')}
    strain_listing_issues = query_strains(release_version=release_version, issues=True)

    return render_template('strain/issues.html', **locals())

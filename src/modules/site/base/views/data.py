import json
from caendr.models.datastore.dataset_release import DatasetRelease
from flask import request, jsonify
import requests
import os

from datetime import timedelta
from simplejson.errors import JSONDecodeError
from flask import make_response, render_template, Blueprint, send_file, url_for, abort

from caendr.services.dataset_release import get_all_releases, get_placeholder_release, get_release_version

from config import config
from extensions import cache
from base.forms import VBrowserForm
from caendr.models.sql import Strain, StrainAnnotatedVariants
from base.utils.auth import jwt_required
from base.api.strain import get_isotypes, query_strains, get_distinct_isotypes


data_bp = Blueprint('data',
                    __name__)

BAM_BAI_DOWNLOAD_SCRIPT_NAME = "bam_bai_signed_download_script.sh"

# ============= #
#   Data Page   #
# ============= #


@data_bp.route('/')
def data_landing():
  disable_parent_breadcrumb = True
  return render_template('data/data_landing.html', **locals())


'''
@data_bp.route('/release/latest')
@data_bp.route('/release/<string:release_version>')
@cache.memoize(50)
def data(release_version=None):
    """
        Default data page - lists
        available releases.
    """
    if release_version is None:
      release_version = config['DATASET_RELEASE']

    # Pre-2020 releases used BAMs grouped by isotype.
    if int(release_version) < 20200101:
        return data_v01(release_version)
    
    # Post-2020 releases keep strain-level bams separate.
    title = "Genomic Data"
    alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.data_landing')}
    sub_page = release_version
    strain_listing = query_strains(release=release_version)
    release_summary = Strain.release_summary(release_version)
    RELEASES = config["RELEASES"]
    DATASET_RELEASE, WORMBASE_release_version = list(filter(lambda x: x[0] == release_version, RELEASES))[0]
    REPORTS = ["alignment"]
    release = DatasetRelease(release_version, report_type='V2')
    f = release.get_report_data_urls_map()
    return render_template('data_v2.html', **locals())'''


@data_bp.route('/release/latest')
@data_bp.route('/release/<string:release_version>')
@cache.memoize(50)
def data(release_version=None):
  """ Default data page - lists available releases. """
  title = "Genomic Data"
  alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.data_landing')}
  RELEASES = get_all_releases()

  # If no releases, create an empty placeholder
  if len(RELEASES) == 0:
    RELEASE = get_placeholder_release()
    release_version = RELEASE.version
    RELEASES = [RELEASE]
  else:
    # Get the requested release and throw an error if it doesn't exist
    if release_version:
      RELEASE = get_release_version(release_version)
      if RELEASE is None:
        abort(422)
    else:
      # Otherwise, show the latest release by default
      RELEASE = RELEASES[0]

  return render_template('data/data.html', **locals())


@cache.memoize(50)
def data_v02(release_version=None):
  title = "Genomic Data"
  alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.data_landing')}
  sub_page = release_version
  strain_listing = query_strains(release=release_version)
  release_summary = Strain.release_summary(release_version)
  RELEASES = config["RELEASES"]
  DATASET_RELEASE, WORMBASE_release_version = list(filter(lambda x: x[0] == release_version, RELEASES))[0]
  REPORTS = ["alignment"]
  release = DatasetRelease(release_version, report_type='V2')
  f = release.get_report_data_urls_map()
  return render_template('data/data_v2.html', **locals())


@cache.memoize(50)
def data_v01(release_version=''):
    # Legacy releases (Pre 20200101)
    title = "Genomic Data"
    alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.data_landing')}
    subtitle = release_version
    strain_listing = query_strains(release=release_version)
    # Fetch variant data
    release = DatasetRelease(version=release_version, report_type='V1')
    f = release.get_report_data_urls_map()
    phylo_url = f.get('phylo_url')
    vcf_summary_url = f.get('vcf_summary_url')

    try:
      vcf_summary = requests.get(vcf_summary_url).json()
    except JSONDecodeError:
      vcf_summary = None

    release_summary = Strain.release_summary(release_version)

    RELEASES = config["RELEASES"]
    wormbase_genome_version = dict(config["RELEASES"])[release_version]
    return render_template('data/data_v1.html', **locals())


# ======================= #
#   Alignment Data Page   #
# ======================= #
@data_bp.route('/release/latest/alignment')
@data_bp.route('/release/<string:release_version>/alignment')
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
    alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.data_landing')}
    strain_listing = query_strains(release=release_version)
    RELEASES = config["RELEASES"]
    DATASET_RELEASE, WORMBASE_VERSION = list(filter(lambda x: x[0] == release_version, RELEASES))[0]
    REPORTS = ["alignment"]
    return render_template('alignment.html', **locals())

# =========================== #
#   Strain Issues Data Page   #
# =========================== #
@data_bp.route('/release/latest/strain_issues')
@data_bp.route('/release/<string:release_version>/strain_issues')
@cache.memoize(50)
def strain_issues(release_version=''):
    """
        Strain Issues page
    """
    if release_version is None:
      release_version = config['DATASET_RELEASE']
    # Pre-2020 releases don't have data organized the same way
    if int(release_version) < 20200101:
        return 
    
    # Post-2020 releases
    title = "Strain Issues"
    alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.data_landing')}
    strain_listing_issues = query_strains(release=release_version, issues=True)
    RELEASES = config["RELEASES"]
    DATASET_RELEASE, WORMBASE_VERSION = list(filter(lambda x: x[0] == release_version, RELEASES))[0]
    return render_template('strain_issues.html', **locals())

# =================== #
#   Download Script   #
# =================== #
@data_bp.route('/release/<string:release_version>/download/download_isotype_bams.sh')
@cache.cached(timeout=60*60*24)
@jwt_required()
def download_script(release_version):
  pass
  '''if not os.path.exists(f'base/{BAM_BAI_DOWNLOAD_SCRIPT_NAME}'):
    download_file(f'bam/{BAM_BAI_DOWNLOAD_SCRIPT_NAME}', f'base/{BAM_BAI_DOWNLOAD_SCRIPT_NAME}')
  return send_file(BAM_BAI_DOWNLOAD_SCRIPT_NAME, as_attachment=True)
'''


@data_bp.route('/release/latest/download/download_strain_bams.sh')
@data_bp.route('/release/<string:release_version>/download/download_strain_bams.sh')
@cache.cached(timeout=60*60*24)
@jwt_required()
def download_script_strain_v2(release_version=None):
  pass
'''  if not os.path.exists(f'base/{BAM_BAI_DOWNLOAD_SCRIPT_NAME}'):
    download_file(f'bam/{BAM_BAI_DOWNLOAD_SCRIPT_NAME}', f'base/{BAM_BAI_DOWNLOAD_SCRIPT_NAME}')
  return send_file(BAM_BAI_DOWNLOAD_SCRIPT_NAME, as_attachment=True)
'''

@data_bp.route('/download/files/<string:blob_name>')
@jwt_required()
def download_bam_url(blob_name=''):
  pass
''' title = blob_name
  blob_path = 'bam/' + blob_name
  signed_download_url = generate_download_signed_url_v4(blob_path)
  msg = 'download will begin shortly...'
  if not signed_download_url:
    msg = 'error fetching download link'
    signed_download_url = ''

  return render_template('download.html', **locals())
'''


# ============= #
#   GBrowser    #
# ============= #

@data_bp.route('/gbrowser')
@data_bp.route('/gbrowser/<int:release>')
@data_bp.route('/gbrowser/<int:release>/<region>')
@data_bp.route('/gbrowser/<int:release>/<region>/<query>')
def gbrowser(release='', region="III:11746923-11750250", query=None):
  pass
'''    VARS = {'title': "Genome Browser",
            'DATASET_RELEASE': int(release),
            'strain_listing': get_isotypes(),
            'region': region,
            'query': query,
            'alt_parent_breadcrumb': {
              "title": "Data", 
              "url": url_for('data.data_landing')
            },
            'fluid_container': True}
    return render_template('gbrowser.html', **VARS)'''


# ============= #
#   VBrowser    #
# ============= #


@data_bp.route('/vbrowser')
def vbrowser():
  title = 'Variant Annotation'
  alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.data_landing')}
  form = VBrowserForm()
  strain_listing = get_distinct_isotypes()
  columns = StrainAnnotatedVariants.column_details
  fluid_container = True
  return render_template('vbrowser.html', **locals())


@data_bp.route('/vbrowser/query/interval', methods=['POST'])
def vbrowser_query_interval():
  title = 'Variant Annotation'
  payload = json.loads(request.data)

  query = payload.get('query')

  is_valid = StrainAnnotatedVariants.verify_interval_query(q=query)
  if is_valid:
    data = StrainAnnotatedVariants.run_interval_query(q=query)
    return jsonify(data)

  return jsonify({})



@data_bp.route('/vbrowser/query/position', methods=['POST'])
def vbrowser_query_position():
  title = 'Variant Annotation'
  payload = json.loads(request.data)

  query = payload.get('query')

  is_valid = StrainAnnotatedVariants.verify_position_query(q=query)
  if is_valid:
    data = StrainAnnotatedVariants.run_position_query(q=query)
    return jsonify(data)

  return jsonify({})



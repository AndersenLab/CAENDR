import re
from caendr.models.datastore.dataset_release import DatasetRelease
from flask import (render_template,
                    Blueprint, 
                    request,
                    url_for)
from extensions import cache

from caendr.api.isotype import get_isotypes
from caendr.services.dataset_release import get_dataset_release, get_latest_dataset_release_version


gene_browser_bp = Blueprint('gene_browser',
                        __name__,
                        template_folder='templates')


def is_valid_release_version(value = None):
  if value is None:
    return False
  return value.isdigit()

def is_valid_wormbase_version(value = None):
  if value is None:
    return False
  regex = r"^ws[0-9]+$"
  return re.match(regex, value, flags=re.IGNORECASE) is not None

def get_dataset_release_or_latest(release_version = None):
  if release_version is None or not is_valid_release_version(release_version):
    return get_latest_dataset_release_version()
  dataset_release = get_dataset_release(release_version)
  if dataset_release is not None:
    dataset_release
  return get_latest_dataset_release_version()


@gene_browser_bp.route('/gbrowser')
@gene_browser_bp.route('/gbrowser/')
@gene_browser_bp.route('/gbrowser/<release_version>')
@gene_browser_bp.route('/gbrowser/<release_version>/<region>')
@gene_browser_bp.route('/gbrowser/<release_version>/<region>/<query>')
@cache.memoize(60*60)
def gbrowser(release_version=None, region="III:11746923-11750250", query=None):
  dataset_release = get_dataset_release_or_latest(release_version)

  wormbase_version_override = request.args.get('wormbase_version', None)
  if (wormbase_version_override is not None) and is_valid_wormbase_version(wormbase_version_override):
    wormbase_version = wormbase_version_override.upper()
  else:
    wormbase_version = dataset_release.wormbase_version    
    # OVERRIDE wormbase_version  (default to 276 until 283 IGB data is available) 
    wormbase_version = 'WS276'

  
  # dataset_release_prefix = f'//storage.googleapis.com/elegansvariation.org/releases'
  dataset_release_prefix = f"//storage.googleapis.com/caendr-site-public-bucket/dataset_release/c_elegans"

  track_url_prefix = f'//storage.googleapis.com/elegansvariation.org/browser_tracks'
  # track_url_prefix = f'//storage.googleapis.com/caendr-site-public-bucket/dataset_release/c_elegans/{dataset_release.version}/browser_tracks'

  bam_bai_url_prefix = f'//storage.googleapis.com/elegansvariation.org/bam'
  
  VARS = {'title': f"Genome Browser",
          'DATASET_RELEASE': int(dataset_release.version),
          'strain_listing': get_isotypes(),
          'region': region,
          'query': query,
          'alt_parent_breadcrumb': {
            "title": "Data", 
            "url": url_for('data.landing')
          },
          'wormbase_version': wormbase_version,
          'release_version': int(dataset_release.version),
          'track_url_prefix': track_url_prefix,
          'bam_bai_url_prefix': bam_bai_url_prefix,
          'dataset_release_prefix': dataset_release_prefix,
          'fluid_container': True}
  return render_template('data/gbrowser.html', **VARS)

import re
from caendr.models.datastore.dataset_release import DatasetRelease
from caendr.models.datastore.settings import Settings
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

def get_dataset_release_or_latest(release_version = None):
  if release_version is None or not is_valid_release_version(release_version):
    return get_latest_dataset_release_version()
  return get_dataset_release(release_version)


@gene_browser_bp.route('/gbrowser')
@gene_browser_bp.route('/gbrowser/<release_version>')
@gene_browser_bp.route('/gbrowser/<release_version>/<region>')
@gene_browser_bp.route('/gbrowser/<release_version>/<region>/<query>')
@cache.memoize(60*60)
def gbrowser(release_version=None, region="III:11746923-11750250", query=None):
  dataset_release = get_dataset_release_or_latest(release_version)
  
  # TODO: Do a look up on release_version if the parameter is not None.
  # Extract .version and .wormbase_version from the release_version object 
  # (DataRelease object)

  base_settings = Settings("base_settings")
  if not base_settings._exists:
    base_settings.save()

  gene_browser_settings = Settings("settings#gene-browser")
  gene_browser_settings.__dict__.update(parent = base_settings)
  gene_browser_settings.save()

  
  if not gene_browser_settings._exists:
    print("creating settings")
    gene_browser_settings.save()

  # TODO: REMOVE TEMP ASSIGNMENTs
  # release_version = '20210121'
  # wormbase_version = 'WS276'
  # wormbase_version = 'WS283'
  track_url_prefix = f'//storage.googleapis.com/elegansvariation.org/browser_tracks'
  bam_bai_url_prefix = f'//storage.googleapis.com/elegansvariation.org/bam'
  dataset_release_prefix = f'//storage.googleapis.com/elegansvariation.org/releases'
  
  
  VARS = {'title': f"Genome Browser",
          'DATASET_RELEASE': int(dataset_release.version),
          'strain_listing': get_isotypes(),
          'region': region,
          'query': query,
          'alt_parent_breadcrumb': {
            "title": "Data", 
            "url": url_for('data.landing')
          },
          'wormbase_version': dataset_release.wormbase_version,
          'release_version': int(dataset_release.version),
          'track_url_prefix': track_url_prefix,
          'bam_bai_url_prefix': bam_bai_url_prefix,
          'dataset_release_prefix': dataset_release_prefix,
          'fluid_container': True}
  return render_template('data/gbrowser.html', **VARS)

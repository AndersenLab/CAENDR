from flask import (render_template,
                    Blueprint, 
                    url_for)

from caendr.api.isotype import get_isotypes
from caendr.services.dataset_release import get_latest_dataset_release_version


gene_browser_bp = Blueprint('gene_browser',
                        __name__,
                        template_folder='templates')


@gene_browser_bp.route('/gbrowser')
@gene_browser_bp.route('/gbrowser/<int:release>')
@gene_browser_bp.route('/gbrowser/<int:release>/<region>')
@gene_browser_bp.route('/gbrowser/<int:release>/<region>/<query>')
def gbrowser(release_version=None, region="III:11746923-11750250", query=None):
  if not release_version:
    release_version = get_latest_dataset_release_version()
  
  # TODO: REMOVE TEMP ASSIGNMENTs
  release_version = '20210121'
  wormbase_version = 'WS276'
  track_url_prefix = f'//storage.googleapis.com/elegansvariation.org/browser_tracks'
  bam_bai_url_prefix = f'//storage.googleapis.com/elegansvariation.org/bam'
  dataset_release_prefix = f'//storage.googleapis.com/elegansvariation.org/releases'
  
  
  VARS = {'title': "Genome Browser",
          'DATASET_RELEASE': int(release_version),
          'strain_listing': get_isotypes(),
          'region': region,
          'query': query,
          'alt_parent_breadcrumb': {
            "title": "Data", 
            "url": url_for('data.landing')
          },
          'wormbase_version': wormbase_version,
          'release_version': int(release_version),
          'track_url_prefix': track_url_prefix,
          'bam_bai_url_prefix': bam_bai_url_prefix,
          'dataset_release_prefix': dataset_release_prefix,
          'fluid_container': True}
  return render_template('data/gbrowser.html', **VARS)

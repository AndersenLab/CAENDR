from flask import render_template, Blueprint, url_for
from base.utils.auth import jwt_required
from extensions import cache

from caendr.api.strain import get_bam_bai_download_link

data_downloads_bp = Blueprint('data_downloads',
                    __name__,
                    template_folder='templates')


@data_downloads_bp.route('/release/latest/download/download_strain_bams.sh')
@data_downloads_bp.route('/release/<string:release_version>/download/download_strain_bams.sh')
@cache.cached(timeout=60*60*24)
@jwt_required()
def download_script_strain_v2(release_version):
  # TODO: write this fn
  pass

@data_downloads_bp.route('/release/<string:release_version>/download/download_isotype_bams.sh')
@cache.cached(timeout=60*60*24)
@jwt_required()
def download_script(release_version):
  # TODO: write this fn
  pass

@data_downloads_bp.route('/download/files/<string:strain_name>/<string:ext>')
@cache.cached(timeout=60*60*1)
@jwt_required()
def download_bam_bai_file(strain_name='', ext=''):
  if ext == 'bai':
    ext = 'bam.bai'
  
  title = f'{strain_name}.{ext}'
  alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.landing')}

  signed_download_url = get_bam_bai_download_link(strain_name, ext)
  msg = 'download will begin shortly...'
  if not signed_download_url:
    msg = 'error fetching download link'
    signed_download_url = ''
  
  return render_template('data/download.html', **locals())


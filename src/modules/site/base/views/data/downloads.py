import os
from flask import render_template, Blueprint, url_for, send_file, abort
from base.utils.auth import jwt_required
from extensions import cache

from caendr.api.strain import get_bam_bai_download_link, fetch_bam_bai_download_script

data_downloads_bp = Blueprint('data_downloads',
                    __name__,
                    template_folder='templates')


@data_downloads_bp.route('/release/latest/download/download_strain_bams.sh')
@data_downloads_bp.route('/release/<string:release_version>/download/download_strain_bams.sh')
@cache.cached(timeout=60*60*24)
@jwt_required()
def download_script_strain_v2(release_version):
  return download_script(release_version)


@data_downloads_bp.route('/release/<string:release_version>/download/download_isotype_bams.sh')
@cache.cached(timeout=60*60*24)
@jwt_required()
def download_script(release_version):
  alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.data')}
  try:
    script_fname = fetch_bam_bai_download_script()
    if script_fname and os.path.exists(script_fname):
      return send_file(script_fname, as_attachment=True)
  except:
    return abort(404, description="BAM/BAI download script not found")


@data_downloads_bp.route('/download/files/<string:strain_name>/<string:ext>')
@cache.memoize(60*60)
@jwt_required()
def download_bam_bai_file(strain_name='', ext=''):
  title = f'{strain_name}.{ext}'
  alt_parent_breadcrumb = {"title": "Data", "url": url_for('data.data')}

  signed_download_url = get_bam_bai_download_link(strain_name, ext)
  msg = 'download will begin shortly...'
  if not signed_download_url:
    msg = 'error fetching download link'
    signed_download_url = ''
  
  return render_template('data/download-redirect.html', **locals())


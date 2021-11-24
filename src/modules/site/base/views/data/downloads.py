from flask import render_template, Blueprint
from base.utils.auth import jwt_required
from extensions import cache

data_downloads_bp = Blueprint('data_downloads',
                    __name__,
                    template_folder='templates')


@data_downloads_bp.route('/release/latest/download/download_strain_bams.sh')
@data_downloads_bp.route('/release/<string:selected_release>/download/download_strain_bams.sh')
@cache.cached(timeout=60*60*24)
@jwt_required()
def download_script_strain_v2(selected_release):
  # TODO: write this fn
  pass

@data_downloads_bp.route('/release/<string:selected_release>/download/download_isotype_bams.sh')
@cache.cached(timeout=60*60*24)
@jwt_required()
def download_script(selected_release):
  # TODO: write this fn
  pass

@data_downloads_bp.route('/download/files/<string:blob_name>')
@cache.cached(timeout=60*60*1)
@jwt_required()
def download_bam_url(blob_name=''):
  # TODO: write this gn
  pass

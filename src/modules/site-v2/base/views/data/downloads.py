import os
from flask import render_template, Blueprint, url_for, send_file, abort, Response, stream_with_context
from base.utils.auth import jwt_required
from extensions import cache

from caendr.api.strain import get_bam_bai_download_link, fetch_bam_bai_download_script, generate_bam_bai_download_script
from caendr.models.datastore import Species
from caendr.models.error import NotFoundError
from caendr.services.dataset_release import get_all_dataset_releases, find_dataset_release
from caendr.utils.env import get_env_var


BAM_BAI_DOWNLOAD_SCRIPT_NAME = get_env_var('BAM_BAI_DOWNLOAD_SCRIPT_NAME', as_template=True)


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


@data_downloads_bp.route('/download/<string:species_name>/<string:strain_name>/<string:ext>')
@cache.memoize(60*60)
@jwt_required()
def download_bam_bai_file(species_name='', strain_name='', ext=''):

  # Parse the species & release from the URL
  try:
    species = Species.get(species_name.replace('-', '_'))
  except NotFoundError:
    return abort(404)

  # Get the download link for this strain
  signed_download_url = get_bam_bai_download_link(species, strain_name, ext) or ''

  return render_template('data/download-redirect.html', **{
    'title': f'{strain_name}.{ext}',
    'alt_parent_breadcrumb': {"title": "Data", "url": url_for('data.data')},

    'signed_download_url': signed_download_url,
    'msg': 'download will begin shortly...' if signed_download_url else 'error fetching download link',
  })


@data_downloads_bp.route('/download/<string:species_name>/<string:release_version>/bam-bai-download-script', methods=['GET'])
def download_bam_bai_script(species_name, release_version):

  # Parse the species & release from the URL
  try:
    species = Species.get(species_name.replace('-', '_'))
    release = find_dataset_release(get_all_dataset_releases(order='-version', species=species.name), release_version)
  except NotFoundError:
    return abort(404)

  # Compute the desired filename from the species & release
  filename = BAM_BAI_DOWNLOAD_SCRIPT_NAME.get_string(**{
    'SPECIES': species.name,
    'RELEASE': release.version,
  })

  # Stream the file as an attachment with the desired filename
  resp = Response(stream_with_context(generate_bam_bai_download_script(species, release)), mimetype='text/plain')
  resp.headers['Content-Disposition'] = f'attachment; filename={ filename }'
  return resp

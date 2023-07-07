from threading import Thread
from flask import jsonify, Blueprint, request, flash, abort, render_template
from caendr.services.logger import logger

from caendr.services.cloud.cron import verify_cron_req_origin
from caendr.api.strain import upload_bam_bai_download_script
from caendr.models.error import APIDeniedError, APIError, NotFoundError
from caendr.models.datastore import Species
from caendr.services.dataset_release import get_all_dataset_releases, find_dataset_release

from base.utils.auth import user_has_role
from base.utils.cache import delete_expired_cache

maintenance_bp = Blueprint('maintenance',
                          __name__)

# TODO: RESTORE THIS FN
@maintenance_bp.route('/cleanup_cache', methods=['GET'])
def cleanup_cache():
  if not (verify_cron_req_origin(request) or user_has_role("admin")):
    # flash('You do not have access to this page', 'error')
    return APIError.default_handler(APIDeniedError)

  result = delete_expired_cache()
  response = jsonify({"result": result})
  response.status_code = 200
  return response
  

# TODO: This is likely obsolete, since the download script is now generated on-demand.
@maintenance_bp.route('/create_bam_bai_download_script/<string:species_name>/<string:release_version>', methods=['GET'])
def create_bam_bai_download_script(species_name, release_version):
  if not (verify_cron_req_origin(request) or user_has_role("admin")):
    return APIError.default_handler(APIDeniedError)

  # Parse the species & release from the URL
  try:
    species = Species.get(species_name.replace('-', '_'))
    release = find_dataset_release(get_all_dataset_releases(order='-version', species=species.name), release_version)
  except NotFoundError:
    return abort(404)

  # Start a thread to generate and upload the file
  # TODO: Should this be signed or unsigned?
  thread = Thread(target=upload_bam_bai_download_script, args={'species': species, 'release': release})
  thread.start()

  response = jsonify({})
  response.status_code = 200
  return response



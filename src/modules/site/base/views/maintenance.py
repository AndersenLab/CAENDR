from threading import Thread
from flask import jsonify, Blueprint, request, flash, abort, render_template
from logzero import logger

from caendr.services.cloud.cron import verify_cron_req_origin
from caendr.api.strain import generate_bam_bai_download_script, get_joined_strain_list
from caendr.models.error import APIDeniedError, APIError

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
  

@maintenance_bp.route('/create_bam_bai_download_script', methods=['GET'])
def create_bam_bai_download_script():
  if not (verify_cron_req_origin(request) or user_has_role("admin")):
    return APIError.default_handler(APIDeniedError)

  joined_strain_list = get_joined_strain_list()
  thread = Thread(target=generate_bam_bai_download_script, args={joined_strain_list: joined_strain_list})
  thread.start()

  response = jsonify({})
  response.status_code = 200
  return response



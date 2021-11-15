import logging
import os

from flask import Blueprint, jsonify, request

from util import extract_json_payload
from caendr.services.error import APIBadRequestError, APIInternalError
from caendr.services.task import update_task_status, verify_task_headers, Task
from caendr.services.pubsub import get_operation
from caendr.services.lifesciences import create_pipeline_status, update_pipeline_status
from pipelines.nemascan import DS_KIND as NEMASCAN_DS_KIND, start_nemascan_pipeline

task_handler_bp = Blueprint('task_bp', __name__)

@task_handler_bp.route('/test', methods=['GET'])
def test_fn():
  return jsonify({'service_account': os.environ.get('NSCALC_SERVICE_ACCOUNT')}), 200


@task_handler_bp.route('/start/<task_route>', methods=['POST'])
def start_task(task_route):
  queue, task = verify_task_headers(task_route)
  logging.info(f"Task: {queue}:{task}")

  payload = extract_json_payload(request)
  logging.info(f"Payload: {payload}")

  # Marshall JSON to Task object
  try:
    task = Task(**payload)
  except:
    raise APIBadRequestError('Task request must include `hash`, `ds_id`, and `ds_kind`')

  # Trigger whichever pipeline was requested
  if task.ds_kind == NEMASCAN_DS_KIND:
    response = start_nemascan_pipeline(task.hash, task.ds_id)
      
  if (response is None) or (response.get('name') is None):
    update_task_status(task, 'ERROR')
    raise APIInternalError('Error starting pipeline')

  operation_id = response.get('name')
  options = response.get('metadata')
  create_pipeline_status(task.hash, operation_id, options)
  update_task_status(task, 'RUNNING', operation_id)

  return jsonify({'operation_id': operation_id}), 200


@task_handler_bp.route('/status/<task_route>', methods=['POST'])
def update_task(task_route):
  payload = extract_json_payload(request)
  logging.info(f"Task Status Payload: {payload}")

  # Marshall JSON to PubSubStatus object
  operation_id = get_operation(payload)
  if operation_id is None:
    raise APIBadRequestError('Error parsing PubSub status message.')
  
  update_pipeline_status(operation_id)

  return jsonify({}), 200
  

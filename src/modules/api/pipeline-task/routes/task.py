import json

from flask import Blueprint, jsonify, request
from caendr.services.logger import logger
from caendr.utils import monitor

from pipelines.utils import update_status_safe, get_task_handler

from caendr.models.error import APIError, APIBadRequestError, APIInternalError, APIUnprocessableEntity
from caendr.models.task import TaskStatus
from caendr.models.pub_sub import PubSubAttributes, PubSubMessage, PubSubStatus

from caendr.services.cloud.task import update_task_status, verify_task_headers
from caendr.services.cloud.pubsub import get_attribute, pubsub_endpoint
from caendr.services.cloud.lifesciences import create_pipeline_operation_record, get_operation_id_from_name
from caendr.services.cloud.utils import update_pipeline_operation_record, update_all_linked_status_records
from caendr.services.persistent_logger import PersistentLogger



monitor.init_sentry("pipeline-task")

task_handler_bp = Blueprint('task_bp', __name__)



@task_handler_bp.route('/start/<task_route>', methods=['POST'])
def start_task(task_route):
  queue, task = verify_task_headers(task_route)
  logger.info(f"Task: {queue}:{task}")

  # Parse request payload
  try:
    payload = json.loads(request.data)
  except:
    raise APIUnprocessableEntity('Failed to parse request body as valid JSON')

  # Get the task ID from the payload
  op_id = payload.get('id', 'no-id')
  if op_id is None:
    logger.error(f'Request body must define an operation ID. Payload: {payload}')
    raise APIUnprocessableEntity('Request body must define an operation ID')

  # Log the start of the task
  call_id = f'TASK {op_id}'
  logger.info(f'[{ call_id }] Starting job in queue { task_route }. Payload: {payload}')

  # Try to create a task handler of the appropriate type
  handler = get_task_handler(task_route, **payload)

  # Run the job
  try:
    exec_id = handler.run(run_if_exists=True)
    update_status_safe(queue, op_id, status=TaskStatus.RUNNING)

  # Intercept API errors to add task ID
  except APIError as ex:
    update_status_safe(queue, op_id, status=TaskStatus.ERROR)
    ex.set_call_id(call_id)
    raise ex

  # Wrap generic exceptions in an Internal Error class
  except Exception as ex:
    update_status_safe(queue, op_id, status=TaskStatus.ERROR)
    raise APIInternalError('Error occurred while creating job', call_id) from ex

  #return jsonify({'operation': op.id}), 200
  return jsonify({}), 200


@task_handler_bp.route('/status', methods=['POST'])
@pubsub_endpoint
def update_task():

  # Parse request payload
  try:
    payload = json.loads(request.data)
    logger.info(f"[STATUS] Payload: {payload}")
  except Exception as ex:
    raise APIUnprocessableEntity('Failed to parse request body as valid JSON') from ex

  # Marshall JSON to PubSubStatus object
  # Get the task ID from the payload (raises an error if not provided)
  operation_name = get_attribute(payload, "operation")

  # String that identifies this API call, for debugging purposes
  call_id = f'STATUS {get_operation_id_from_name(operation_name)}'


  # Update the operation record itself
  logger.debug(f"[{ call_id }] Updating the pipeline operation record...")
  try:
    op = update_pipeline_operation_record(operation_name)

  # Intercept API errors to add task ID
  except APIError as ex:
    ex.set_call_id(call_id)
    raise ex

  # Wrap generic exceptions in an Internal Error class
  except Exception as ex:
    raise APIInternalError('Error updating pipeline operation record', call_id) from ex


  # Update all linked report entities
  try:
    logger.debug(f"[{ call_id }] Updating all linked status records for operation {op}: {dict(op)}")
    update_all_linked_status_records(op['operation_kind'], op['operation'])

  # Intercept API errors to add task ID
  except APIError as ex:
    ex.set_call_id(call_id)
    raise ex

  # Wrap generic exceptions in an Internal Error class
  except Exception as ex:
    raise APIInternalError(f"Error updating status record(s)", call_id) from ex


  # If the job has finished or errored out, acknowledge the Pub/Sub message
  # If the job is still running, don't acknowledge -- tells Pub/Sub to try the request again
  # Return as bool value to be handled by pubsub_endpoint decorator
  return op['done'] or op['error']

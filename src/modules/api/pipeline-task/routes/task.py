import json

from flask import Blueprint, jsonify, request
from caendr.services.logger import logger
from caendr.utils import monitor

from pipelines.utils import update_status_safe, get_task_handler, get_runner_from_operation_name

from caendr.models.error import APIError, APIBadRequestError, APIInternalError, APIUnprocessableEntity
from caendr.models.status import JobStatus
from caendr.models.pub_sub import PubSubAttributes, PubSubMessage, PubSubStatus

from caendr.services.cloud.task import update_task_status, verify_task_headers
from caendr.services.cloud.pubsub import get_attribute, pubsub_endpoint
from caendr.services.cloud.lifesciences import get_operation_id_from_name
from caendr.services.cloud.utils import update_all_linked_status_records
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
    update_status_safe(handler, JobStatus.RUNNING, call_id)

  # Intercept API errors to add task ID
  except APIError as ex:
    update_status_safe(handler, JobStatus.ERROR, call_id)
    ex.set_call_id(call_id)
    raise ex

  # Wrap generic exceptions in an Internal Error class
  except Exception as ex:
    update_status_safe(handler, JobStatus.ERROR, call_id)
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

  # Get a runner object and execution ID representing this job from the operation name
  logger.debug(f"[{ call_id }] Retrieving the operation...")
  try:
    runner, exec_id = get_runner_from_operation_name(operation_name)

  # Intercept API errors to add task ID
  except APIError as ex:
    ex.set_call_id(call_id)
    raise ex

  # Wrap generic exceptions in an Internal Error class
  except Exception as ex:
    raise APIInternalError('Error getting pipeline runner', call_id) from ex

  # Make sure a job execution is specified
  if exec_id is None:
    raise APIBadRequestError('Operation name must specify a job execution.', call_id)


  # Get the current status of the job, updating the PipelineOperation record implicitly
  logger.debug(f"[{ call_id }] Checking the operation status and updating the PipelineOperation record...")
  status = runner.check_status(exec_id)


  # Update all linked report entities
  try:
    logger.debug(f"[{ call_id }] Updating all linked status records to status { status }...")
    update_all_linked_status_records(runner, exec_id, status)

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
  return status in JobStatus.FINISHED

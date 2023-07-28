import json

from flask import Blueprint, jsonify, request
from caendr.services.logger import logger
from caendr.utils import monitor

from pipelines.utils import start_job, update_status_safe

from caendr.models.error import APIError, APIBadRequestError, APIInternalError, APIUnprocessableEntity
from caendr.models.task import TaskStatus
from caendr.models.pub_sub import PubSubAttributes, PubSubMessage, PubSubStatus

from caendr.services.cloud.task import update_task_status, verify_task_headers
from caendr.services.cloud.pubsub import get_operation
from caendr.services.cloud.lifesciences import create_pipeline_operation_record, update_pipeline_operation_record, update_all_linked_status_records, get_operation_id_from_name
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
  op_id = payload.get('id')
  if op_id is None:
    logger.error(f'Request body must define an operation ID. Payload: {payload}')
    raise APIUnprocessableEntity('Request body must define an operation ID')
  else:
    logger.info(f"[TASK {op_id}] Payload: {payload}")


  # Create & start the job
  try:
    handler, create_response, run_response = start_job(payload, task_route, run_if_exists=True)
    update_status_safe(queue, op_id, status=TaskStatus.RUNNING)

  # Intercept API errors to add task ID
  except APIError as ex:
    update_status_safe(queue, op_id, status=TaskStatus.ERROR)
    ex.set_call_id(f'TASK {op_id}')
    raise ex

  # Wrap generic exceptions in an Internal Error class
  except Exception as ex:
    update_status_safe(queue, op_id, status=TaskStatus.ERROR)
    raise APIInternalError('Failed to create job', f'TASK {op_id}') from ex


  # Create a Pipeline Operation record for the task
  try:
    op = create_pipeline_operation_record(handler.task, run_response)
    update_status_safe(queue, op_id, operation_name=op.operation)

  # Intercept API errors to add task ID
  except APIError as ex:
    ex.set_call_id(f'TASK {op_id}')
    raise ex

  # Wrap generic exceptions in an Internal Error class
  # TODO: Do we need to send anything to the persistent logger?
  except Exception as ex:
    # persistent_logger = PersistentLogger(task_route)
    raise APIInternalError('Could not create pipeline_operation record', f'TASK { op_id }') from ex

  #return jsonify({'operation': op.id}), 200
  return jsonify({}), 200


@task_handler_bp.route('/status', methods=['POST'])
def update_task():
  try:
    try:
      payload = json.loads(request.data)
      logger.info(f"Task Status Payload: {payload}")
    except Exception as e:
      logger.error(e)
      raise APIBadRequestError('Error parsing JSON payload')

    # Marshall JSON to PubSubStatus object
    try:
      operation = payload.get('message').get("attributes").get("operation")
      op_id = get_operation_id_from_name(operation)
    except Exception as e:
      logger.error(e)
      raise APIBadRequestError('Error parsing PubSub status message.')

    try:
      logger.debug(f"[STATUS {op_id}] Updating the pipeline operation record...")
      op = update_pipeline_operation_record(operation)
      if op == None:
        logger.warn(f"[STATUS {op_id}] Nothing to do. GLS operation could not be found. bailing out.")
        return jsonify({'status': 'NOT_FOUND'}), 404

      logger.debug(f"[STATUS {op_id}] Updating all linked status records for operation {op}: {dict(op)}")
      update_all_linked_status_records(op['operation_kind'], operation)
      logger.debug(operation)
    except Exception as e:
      logger.error(f"[STATUS {op_id}] Unable to update pipeline record[s]: {e}")
      raise APIInternalError(f"Error updating status records. Error: {e}")

  except Exception as error:
    logger.error(f"Error updating records for operation. {type(error).__name__}: {str(error)}")
    return jsonify({'error': f"{type(error).__name__}: {str(error)}" }), 500

  return jsonify({'status': 'OK'}), 200

from caendr.services.logger import logger
import os
import json
from googleapiclient.errors import HttpError

from flask import Blueprint, jsonify, request

from pipelines.task_handler import DatabaseOperationTaskHandler, IndelFinderTaskHandler, HeritabilityTaskHandler, NemascanTaskHandler

from caendr.models.datastore import Species
from caendr.models.error import APIError, APIBadRequestError, APIInternalError, NotFoundError
from caendr.models.task import TaskStatus
from caendr.models.pub_sub import PubSubAttributes, PubSubMessage, PubSubStatus

from caendr.services.cloud.task import update_task_status, verify_task_headers
from caendr.services.cloud.pubsub import get_operation
from caendr.services.cloud.lifesciences import create_pipeline_operation_record, update_pipeline_operation_record, update_all_linked_status_records, get_operation_id_from_name

from caendr.services.nemascan_mapping import update_nemascan_mapping_status
from caendr.services.database_operation import update_db_op_status
from caendr.services.indel_primer import update_indel_primer_status
from caendr.services.heritability_report import update_heritability_report_status
from caendr.services.persistent_logger import PersistentLogger

from caendr.utils import monitor

monitor.init_sentry("pipeline-task")

INDEL_PRIMER_TASK_QUEUE_NAME = os.environ.get('INDEL_PRIMER_TASK_QUEUE_NAME')
NEMASCAN_TASK_QUEUE_NAME = os.environ.get('NEMASCAN_TASK_QUEUE_NAME')
HERITABILITY_TASK_QUEUE_NAME = os.environ.get('HERITABILITY_TASK_QUEUE_NAME')
MODULE_DB_OPERATIONS_TASK_QUEUE_NAME = os.environ.get('MODULE_DB_OPERATIONS_TASK_QUEUE_NAME')

task_handler_bp = Blueprint('task_bp', __name__)




@task_handler_bp.route('/start/<task_route>', methods=['POST'])
def start_task(task_route):
  queue, task = verify_task_headers(task_route)
  logger.info(f"Task: {queue}:{task}")

  try:
    payload = json.loads(request.data)
  except:
    raise APIBadRequestError('Failed to parse request body as valid JSON')

  op_id = payload.get('id')
  if op_id is None:
    logger.error(f'Request body must define an operation ID. Payload: {payload}')
    raise APIBadRequestError('Request body must define an operation ID')
  else:
    logger.info(f"[TASK {op_id}] Payload: {payload}")

  handle_task(payload, task_route, run_if_exists=True)

  #return jsonify({'operation': op.id}), 200
  return jsonify({}), 200


def _get_task_handler(queue_name, *args, **kwargs):
  mapping = {
    MODULE_DB_OPERATIONS_TASK_QUEUE_NAME: DatabaseOperationTaskHandler,
    INDEL_PRIMER_TASK_QUEUE_NAME:         IndelFinderTaskHandler,
    HERITABILITY_TASK_QUEUE_NAME:         HeritabilityTaskHandler,
    NEMASCAN_TASK_QUEUE_NAME:             NemascanTaskHandler,
  }
  cls = mapping.get(queue_name, None)

  if cls is None:
    raise APIBadRequestError(f'Invalid task route {queue_name}.')

  try:
    return cls(*args, **kwargs)

  except NotFoundError as ex:
    if ex.kind == Species.kind:
      raise APIBadRequestError(f'{ cls._Entity_Class.kind } task has invalid species value.') from ex
    else:
      raise APIBadRequestError(f'Could not find { cls._Entity_Class.kind } object wih this ID.') from ex


def _update_status(handler, *args, **kwargs):
  mapping = {
    DatabaseOperationTaskHandler._Entity_Class.kind: update_db_op_status,
    IndelFinderTaskHandler._Entity_Class.kind:       update_indel_primer_status,
    HeritabilityTaskHandler._Entity_Class.kind:      update_heritability_report_status,
    NemascanTaskHandler._Entity_Class.kind:          update_nemascan_mapping_status,
  }
  return mapping[handler.kind](handler.task.id, *args, **kwargs)


def handle_task(payload, task_route, run_if_exists=False):
  call_id = f"TASK { payload.get('id', 'no-id') }"
  logger.info(f"[{ call_id }] handle_task: {task_route}")

  # Try to create a task handler of the appropriate type
  try:
    handler = _get_task_handler(task_route, **payload)

  # Intercept API errors to add task ID
  except APIError as ex:
    ex.set_call_id(call_id)
    raise ex

  # Create a CloudRun job for this task
  try:
    create_response = handler.create_job()

  # If the job already exists, optionally bail out
  except HttpError as ex:
    if run_if_exists and ex.status_code == 409:
      logger.warn(f'[{ call_id }] Encountered HttpError: {ex}')
      logger.warn(f'[{ call_id }] Running job again...')
    else:
      raise APIBadRequestError(f'Failed to create job.', call_id) from ex

  # Wrap any other error in an API Bad Request error
  except Exception as ex:
    raise APIBadRequestError(f'Failed to create job.', call_id) from ex

  # Run the CloudRun job
  try:
    run_response = handler.run_job()

  # Intercept any exceptions and try setting the task status to Error
  except Exception as ex_outer:
    try:
      _update_status(handler, status=TaskStatus.ERROR)
    except Exception as ex_inner:
      logger.error(f'[{ call_id }] Failed to update status to {TaskStatus.ERROR}: {ex_inner}')
    raise ex_outer

  persistent_logger = PersistentLogger(task_route)

  status = TaskStatus.RUNNING
  operation_name = ''
  try:
    op = create_pipeline_operation_record(handler.task, run_response)
    operation_name = op.operation

  except Exception as e:
    msg = f"[{ call_id }] Error: {e}"
    logger.error(msg)
    persistent_logger.log(msg)
    status = TaskStatus.ERROR

  _update_status(handler, status=status, operation_name=operation_name)


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

from caendr.services.logger import logger
import os
import json

from flask import Blueprint, jsonify, request

from pipelines.nemascan import start_nemascan_pipeline
from pipelines.db_op import start_db_op_pipeline
from pipelines.indel_primer import start_indel_primer_pipeline
from pipelines.heritability import start_heritability_pipeline

from caendr.models.datastore.nemascan_mapping import NemascanMapping
from caendr.models.datastore.database_operation import DatabaseOperation
from caendr.models.datastore.indel_primer import IndelPrimer
from caendr.models.datastore.heritability_report import HeritabilityReport

from caendr.models.error import APIBadRequestError, APIInternalError
from caendr.models.task import TaskStatus, NemaScanTask, DatabaseOperationTask, IndelPrimerTask, HeritabilityTask
from caendr.models.pub_sub import PubSubAttributes, PubSubMessage, PubSubStatus

from caendr.services.cloud.task import update_task_status, verify_task_headers
from caendr.services.cloud.pubsub import get_operation
from caendr.services.cloud.lifesciences import create_pipeline_operation_record, update_pipeline_operation_record, update_all_linked_status_records

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

  logger.info(f"Payload: {payload}")
  handle_task(payload, task_route)

  #return jsonify({'operation': op.id}), 200
  return jsonify({}), 200

# Track the 'class' to create the task and the 'function' to initiate the pipeline
def _get_task_metadata(queue_name):
  mapping = {
    NEMASCAN_TASK_QUEUE_NAME: {
      'class': NemaScanTask,
      'start_pipeline': start_nemascan_pipeline,
      'update_status': update_nemascan_mapping_status
    },
    INDEL_PRIMER_TASK_QUEUE_NAME: {
      'class': IndelPrimerTask,
      'start_pipeline': start_indel_primer_pipeline,
      'update_status': update_indel_primer_status
    },
    HERITABILITY_TASK_QUEUE_NAME: {
      'class': HeritabilityTask,
      'start_pipeline':start_heritability_pipeline,
      'update_status': update_heritability_report_status
    },
    MODULE_DB_OPERATIONS_TASK_QUEUE_NAME: {
      'class': DatabaseOperationTask,
      'start_pipeline': start_db_op_pipeline,
      'update_status': update_db_op_status
    }
  }
  return mapping.get(queue_name, None)

def handle_task(payload, task_route):
  logger.info(f"Task: {task_route}")

  task_metadata = _get_task_metadata(task_route)
  task_class, start_pipeline, update_status = task_metadata.values()

  if task_class is None:
      raise APIBadRequestError("Invalid task route")

  task = task_class(**payload)
  response = start_pipeline(task)

  persistent_logger = PersistentLogger(task_route)

  # status = 'RUNNING'
  status = TaskStatus.RUNNING
  operation_name = ''
  try:
    op = create_pipeline_operation_record(task, response)
    operation_name = op.operation
  except Exception as e:
    logger.error(e)
    persistent_logger.log(e)
    status = 'ERROR'

  update_status(task.id, status=status, operation_name=operation_name)


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
    except Exception as e:
      logger.error(e)
      raise APIBadRequestError('Error parsing PubSub status message.')

    try:
      logger.debug("updating the pipeline operation record...")
      op = update_pipeline_operation_record(operation)

      logger.debug(f"updating all linked status records for operation {op}: {dict(op)}")
      update_all_linked_status_records(op['operation_kind'], operation)
      logger.debug(operation)
    except Exception as e:
      logger.error(f"Unable to update pipeline record[s]: {e}")
      raise APIInternalError(f"Error updating status records. Error: {e}")

  except Exception as error:
    logger.error(f"Error updating records for operation. {type(error).__name__}: {str(error)}")
    return jsonify({'error': f"{type(error).__name__}: {str(error)}" }), 500

  return jsonify({'status': 'OK'}), 200

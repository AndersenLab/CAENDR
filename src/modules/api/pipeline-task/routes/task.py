from logzero import logger
import os

from flask import Blueprint, jsonify, request

from pipelines.nemascan import start_nemascan_pipeline
from pipelines.db_op import start_db_op_pipeline
from pipelines.indel_primer import start_indel_primer_pipeline
from pipelines.heritability import start_heritability_pipeline
from pipelines.gene_browser_tracks import start_gene_browser_tracks_pipeline

from caendr.models.datastore.nemascan_mapping import NemascanMapping
from caendr.models.datastore.database_operation import DatabaseOperation
from caendr.models.datastore.indel_primer import IndelPrimer
from caendr.models.datastore.heritability_report import HeritabilityReport
from caendr.models.datastore.gene_browser_tracks import GeneBrowserTracks

from caendr.models.error import APIBadRequestError, APIInternalError
from caendr.models.task import NemaScanTask, DatabaseOperationTask, IndelPrimerTask, HeritabilityTask, GeneBrowserTracksTask
from caendr.models.pub_sub import PubSubAttributes, PubSubMessage, PubSubStatus

from caendr.services.cloud.task import update_task_status, verify_task_headers
from caendr.services.cloud.pubsub import get_operation
from caendr.services.cloud.lifesciences import create_pipeline_operation_record, update_pipeline_operation_record, update_all_linked_status_records

from caendr.services.nemascan_mapping import update_nemascan_mapping_status
from caendr.services.database_operation import update_db_op_status
from caendr.services.indel_primer import update_indel_primer_status
from caendr.services.heritability_report import update_heritability_report_status
from caendr.services.gene_browser_tracks import update_gene_browser_track_status
from caendr.services.persistent_logger import PersistentLogger

from caendr.utils.json import extract_json_payload
from caendr.utils import monitor

monitor.init_sentry("pipeline-task")

INDEL_PRIMER_TASK_QUEUE_NAME = os.environ.get('INDEL_PRIMER_TASK_QUEUE_NAME')
NEMASCAN_TASK_QUEUE_NAME = os.environ.get('NEMASCAN_TASK_QUEUE_NAME')
HERITABILITY_TASK_QUEUE_NAME = os.environ.get('HERITABILITY_TASK_QUEUE_NAME')
MODULE_DB_OPERATIONS_TASK_QUEUE_NAME = os.environ.get('MODULE_DB_OPERATIONS_TASK_QUEUE_NAME')
MODULE_GENE_BROWSER_TRACKS_TASK_QUEUE_NAME = os.environ.get('MODULE_GENE_BROWSER_TRACKS_TASK_QUEUE_NAME')

task_handler_bp = Blueprint('task_bp', __name__)




@task_handler_bp.route('/start/<task_route>', methods=['POST'])
def start_task(task_route):
  queue, task = verify_task_headers(task_route)
  logger.info(f"Task: {queue}:{task}")

  try:
    payload = extract_json_payload(request)
  except:
    raise APIBadRequestError('Failed to parse request body as valid JSON')

  logger.info(f"Payload: {payload}")
  handle_task(payload, task_route)

  #return jsonify({'operation': op.id}), 200
  return jsonify({}), 200


def _get_task_class(queue_name):
  mapping = {
    NEMASCAN_TASK_QUEUE_NAME: NemaScanTask,
    INDEL_PRIMER_TASK_QUEUE_NAME: IndelPrimerTask,
    HERITABILITY_TASK_QUEUE_NAME: HeritabilityTask,
    MODULE_DB_OPERATIONS_TASK_QUEUE_NAME: DatabaseOperationTask,
    MODULE_GENE_BROWSER_TRACKS_TASK_QUEUE_NAME: GeneBrowserTracksTask
  }
  return mapping.get(queue_name, None)

def _create_task(task_route, payload):
  TaskClass = _get_task_class(task_route)
  if TaskClass is None:
    raise APIBadRequestError("Invalid task route")
  task = TaskClass(**payload)
  return task

def handle_task(payload, task_route):
  logger.info(f"Task: {task_route}")

  task = _create_task(task_route, payload)
  # response = start_nemascan_pipeline(task)

  if task_route == NEMASCAN_TASK_QUEUE_NAME:
    # task = NemaScanTask(**payload)
    response = start_nemascan_pipeline(task)
  elif task_route == INDEL_PRIMER_TASK_QUEUE_NAME:
    # task = IndelPrimerTask(**payload)
    response = start_indel_primer_pipeline(task)
  elif task_route == HERITABILITY_TASK_QUEUE_NAME:
    # task = HeritabilityTask(**payload)
    response = start_heritability_pipeline(task)
  elif task_route == MODULE_DB_OPERATIONS_TASK_QUEUE_NAME:
    # task = DatabaseOperationTask(**payload)
    response = start_db_op_pipeline(task)
  elif task_route == MODULE_GENE_BROWSER_TRACKS_TASK_QUEUE_NAME:
    # task = GeneBrowserTracksTask(**payload)
    response = start_gene_browser_tracks_pipeline(task)
  else:
    logger.warn(f"Unknown task route: {task_route}")
    return

  persistent_logger = PersistentLogger(task_route)

  logger.debug(task_route)
  status = 'RUNNING'
  operation_name = ''
  try:
    op = create_pipeline_operation_record(task, response)
    operation_name = op.operation
  except Exception as e:
    logger.error(e)
    persistent_logger.log(e)
    status = 'ERROR'

  if task.kind == NemascanMapping.kind:
    update_nemascan_mapping_status(task.id, status=status, operation_name=operation_name)
  elif task.kind == IndelPrimer.kind:
    update_indel_primer_status(task.id, status=status, operation_name=operation_name)
  elif task.kind == HeritabilityReport.kind:
    update_heritability_report_status(task.id, status=status, operation_name=operation_name)
  elif task.kind == DatabaseOperation.kind:
    update_db_op_status(task.id, status=status, operation_name=operation_name)
  elif task.kind == GeneBrowserTracks.kind:
    update_gene_browser_track_status(task.id, status=status, operation_name=operation_name)
  else:
    logger.warn(f"Unknown task kind: {task.kind}")    


@task_handler_bp.route('/status', methods=['POST'])
def update_task():
  try:
    try:
      payload = extract_json_payload(request)
      logger.info(f"Task Status Payload: {payload}")
    except Exception as e:
      logger.error(e)
      raise APIBadRequestError('Error parsing JSON payload')

    # Marshall JSON to PubSubStatus object
    try:
      message = payload.get('message')
      attributes = message.get('attributes')
      operation = attributes.get('operation')
    except Exception as e:
      logger.error(e)
      raise APIBadRequestError('Error parsing PubSub status message.')

    try:
      logger.debug("updating the pipeline operation record...")
      op = update_pipeline_operation_record(operation)

      logger.debug(f"updating all linked status records for operation: {op}")
      update_all_linked_status_records(op.operation_kind, operation)
      logger.debug(operation)
    except Exception as e:
      logger.error(f"Unable to update pipeline record[s]: {e}")
      raise APIInternalError('Error updating status records')
  except Exception as e:
    logger.error(e)
    pass
  return jsonify({}), 200

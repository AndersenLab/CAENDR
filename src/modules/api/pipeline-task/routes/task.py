from logzero import logger
import os

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
from caendr.models.task import NemaScanTask, DatabaseOperationTask, IndelPrimerTask, HeritabilityTask
from caendr.models.pub_sub import PubSubAttributes, PubSubMessage, PubSubStatus

from caendr.services.cloud.task import update_task_status, verify_task_headers
from caendr.services.cloud.pubsub import get_operation
from caendr.services.cloud.lifesciences import create_pipeline_operation_record, update_pipeline_operation_record, update_all_linked_status_records

from caendr.services.nemascan_mapping import update_nemascan_mapping_status
from caendr.services.database_operation import update_db_op_status
from caendr.services.indel_primer import update_indel_primer_status
from caendr.services.heritability_report import update_heritability_report_status

from caendr.utils.json import extract_json_payload

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
    payload = extract_json_payload(request)
  except:
    raise APIBadRequestError('Failed to parse request body as valid JSON')
  
  logger.info(f"Payload: {payload}")
  handle_task(payload, task_route)

  #return jsonify({'operation': op.id}), 200
  return jsonify({}), 200


def handle_task(payload, task_route):
  if task_route == NEMASCAN_TASK_QUEUE_NAME:
    task = NemaScanTask(**payload)
    response = start_nemascan_pipeline(task)
  elif task_route == INDEL_PRIMER_TASK_QUEUE_NAME:
    task = IndelPrimerTask(**payload)
    response = start_indel_primer_pipeline(task)
  elif task_route == HERITABILITY_TASK_QUEUE_NAME:
    task = HeritabilityTask(**payload)
    response = start_heritability_pipeline(task)
  elif task_route == MODULE_DB_OPERATIONS_TASK_QUEUE_NAME:
    task = DatabaseOperationTask(**payload)
    response = start_db_op_pipeline(task)      
  
  status = 'RUNNING'
  operation_name = ''
  try: 
    op = create_pipeline_operation_record(task, response)
    operation_name = op.operation
  except Exception as e:
    logger.error(e)
    status = 'ERROR'
  
  if task.kind == NemascanMapping.kind:
    update_nemascan_mapping_status(task.id, status=status, operation_name=operation_name)
  elif task.kind == IndelPrimer.kind:
    update_indel_primer_status(task.id, status=status, operation_name=operation_name)
  elif task.kind == HeritabilityReport.kind:
    update_heritability_report_status(task.id, status=status, operation_name=operation_name)
  elif task.kind == DatabaseOperation.kind:
    update_db_op_status(task.id, status=status, operation_name=operation_name)
  

@task_handler_bp.route('/status', methods=['POST'])
def update_task():
  try:
    try:
      payload = extract_json_payload(request)
      logger.info(f"Task Status Payload: {payload}")
    except:
      raise APIBadRequestError('Error parsing JSON payload')

    # Marshall JSON to PubSubStatus object
    try:
      message = payload.get('message')
      attributes = message.get('attributes')
      operation = attributes.get('operation')
    except:
      raise APIBadRequestError('Error parsing PubSub status message.')

    try:
      op = update_pipeline_operation_record(operation)
      logger.debug(op)
      update_all_linked_status_records(op.operation_kind, operation)
      logger.debug(operation)
    except:
      raise APIInternalError('Error updating status records')
  except:
    pass
  return jsonify({}), 200

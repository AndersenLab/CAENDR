import os
from caendr.models.datastore.heritability_report import HeritabilityReport

from caendr.services.logger import logger
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials

from caendr.models.datastore import PipelineOperation, DatabaseOperation, NemascanMapping, IndelPrimer
from caendr.models.error import PipelineRunError
from caendr.services.cloud.datastore import query_ds_entities
from caendr.services.cloud.service_account import authenticate_google_service
from caendr.services.cloud.secret import get_secret
from caendr.utils.json import get_json_from_class

GOOGLE_CLOUD_PROJECT_NUMBER = os.environ.get('GOOGLE_CLOUD_PROJECT_NUMBER')
GOOGLE_CLOUD_REGION = os.environ.get('GOOGLE_CLOUD_REGION')
MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME')

#sa_private_key_b64 = get_secret(MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME)
#gls_service = authenticate_google_service(sa_private_key_b64, None, 'lifesciences', 'v2beta')
gls_service = discovery.build('lifesciences', 'v2beta', credentials=GoogleCredentials.get_application_default())

parent_id = f"projects/{GOOGLE_CLOUD_PROJECT_NUMBER}/locations/{GOOGLE_CLOUD_REGION}"


def start_pipeline(pipeline_request):
  req_body = get_json_from_class(pipeline_request)
  logger.debug(f'Starting Pipeline Request: {req_body}')

  try:
    request = gls_service.projects().locations().pipelines().run(parent=parent_id, body=req_body)
    response = request.execute()
    logger.debug(f'Pipeline Response: {response}')
    return response
  except Exception as err:
    logger.error(f"pipeline error: {err}")
    raise PipelineRunError(err)


def create_pipeline_operation_record(task, response):
  if response is None:
    raise PipelineRunError()

  name = response.get('name')
  metadata = response.get('metadata')
  if name is None or metadata is None:
    raise PipelineRunError('Pipeline start response missing expected properties')

  id = name.rsplit('/', 1)[-1]
  data = {
    'id': id,
    'operation': name,
    'operation_kind': task.kind,
    'metadata': metadata,
    'report_path': None,
    'done': False,
    'error': False
  }
  op = PipelineOperation(id)
  op.set_properties(**data)
  op.save()
  return PipelineOperation(id)


def get_pipeline_status(operation_name):
  logger.debug(f'get_pipeline_status: operation_name:{operation_name}')
  request = gls_service.projects().locations().operations().get(name=operation_name)
  response = request.execute()
  logger.debug(response)
  return response


def update_pipeline_operation_record(operation_name):
  logger.debug(f'update_pipeline_operation_record: operation_name:{operation_name}')

  status = get_pipeline_status(operation_name)
  id = operation_name.rsplit('/', 1)[-1]
  data = {
    'done': status.get('done'),
    'error': status.get('error')
  }
  op = PipelineOperation(id)
  op.set_properties(**data)
  op.save()
  return PipelineOperation(id)


def update_all_linked_status_records(kind, operation_name):
  logger.debug(f'update_all_linked_status_records: kind:{kind} operation_name:{operation_name}')
  status = get_pipeline_status(operation_name)
  done = status.get('done')
  error = status.get('error')
  if done:
    status = "COMPLETE"
    if error:
      status = "ERROR"
  else:
    status = "RUNNING"

  filters=[("operation_name", "=", operation_name)]
  ds_entities = query_ds_entities(kind, filters=filters, keys_only=True)
  for entity in ds_entities:
    if kind == DatabaseOperation.kind:
      status_record = DatabaseOperation(entity.key.name)
    elif kind == IndelPrimer.kind:
      status_record = IndelPrimer(entity.key.name)
    elif kind == NemascanMapping.kind:
      status_record = NemascanMapping(entity.key.name)
    elif kind == HeritabilityReport.kind:
      status_record = HeritabilityReport(entity.key.name)
    else:
      logger.warn(f"Unrecognized kind: {kind}")
      continue

    status_record.set_properties(status=status)
    status_record.save()

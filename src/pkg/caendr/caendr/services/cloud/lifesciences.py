import os

from logzero import logger
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials

from caendr.models.datastore import PipelineOperation
from caendr.models.error import PipelineRunError
from caendr.utils.json import get_json_from_class
from caendr.services.cloud.service_account import authenticate_google_service
from caendr.services.cloud.secret import get_secret

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
    'metadata': metadata,
    'report_path': None,
    'done': False,
    'error': False
  }
  op = PipelineOperation(id)
  op.set_properties(**data)
  op.save()
  return op


def update_pipeline_operation_record(operation_id):
  logger.debug(f'update_pipeline_operation_record: operation_id:{operation_id}')
  request = gls_service.projects().locations().operations().get(name=operation_id)
  response = request.execute()
  
  # TODO: WRITE THIS!
'''
  gls_entity = query_ds_entities(GLS_OPERATION_ENTITY, 'operation', operation_id)

  if response is not None:
    data = {
      'done': response.get('done', False),
      'error': response.get('error', False)
    }
    return update_ds_entity(gls_entity, data)'''
    

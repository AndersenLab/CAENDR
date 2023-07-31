import os

from caendr.services.logger import logger
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials

from caendr.models.datastore import PipelineOperation
from caendr.models.error import PipelineRunError
from caendr.services.cloud.service_account import authenticate_google_service
from caendr.utils.env import get_env_var
from caendr.utils.json import get_json_from_class


GOOGLE_CLOUD_PROJECT_NUMBER = os.environ.get('GOOGLE_CLOUD_PROJECT_NUMBER')
GOOGLE_CLOUD_REGION = os.environ.get('GOOGLE_CLOUD_REGION')
MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME = os.environ.get('MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME')



#sa_private_key_b64 = get_secret(MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME)
#gls_service = authenticate_google_service(sa_private_key_b64, None, 'lifesciences', 'v2beta')
gls_service = discovery.build('lifesciences', 'v2beta', credentials=GoogleCredentials.get_application_default())

parent_id = f"projects/{GOOGLE_CLOUD_PROJECT_NUMBER}/locations/{GOOGLE_CLOUD_REGION}"


def get_operation_id_from_name(operation_name):
  try:
    return operation_name.rsplit('/', 1)[-1]
  except:
    logger.warn(f'Could not parse operation ID from operation_name "{operation_name}"')
    return operation_name


def start_pipeline(task_id, pipeline_request):
  req_body = get_json_from_class(pipeline_request)
  logger.debug(f'[TASK {task_id}] Starting Pipeline Request: {req_body}')

  try:
    request = gls_service.projects().locations().pipelines().run(parent=parent_id, body=req_body)
    response = request.execute()
    logger.debug(f'[TASK {task_id}] Pipeline Response: {response}')
    return response
  except Exception as err:
    logger.error(f"[TASK {task_id}] Pipeline Error: {err}")
    raise PipelineRunError(err)


def create_pipeline_operation_record(task, response):
  if response is None:
    raise PipelineRunError()

  try:
    name = response.get('response').get('name')
  except:
    name = response.get('name')
  metadata = response.get('metadata')
  if name is None or metadata is None:
    raise PipelineRunError(f'Pipeline start response missing expected properties (name = "{name}", metadata = "{metadata}")')

  id = get_operation_id_from_name(name)
  op = PipelineOperation(id)
  if op._exists:
    logger.warn(f'[CREATE {id}] PipelineOperation object with ID {id} already exists: {dict(op)}')

  op.set_properties(**{
    'id': id,
    'operation': name,
    'operation_kind': task.kind,
    'metadata': metadata,
    'report_path': None,
    'done': False,
    'error': False
  })
  op.save()
  return op


def get_pipeline_status(operation_name):
  """Return pipeline status
  Retrieves and returns the status for a pipeline
  Args:
    operation_name (string): The name of the operation
  Sample Args:
    operation_name = "projects/111111111111/locations/us-central1/operations/1111111111111111111"

  Return:
    {} (GlS Request Response)
  Sample Return:
    {
      done: true
    }
  """
  logger.debug(f'get_pipeline_status: operation_name:{operation_name}')
  request = gls_service.projects().locations().operations().get(name=operation_name)
  response = request.execute()

  id = get_operation_id_from_name(operation_name)
  logger.debug(f'[STATUS {id}] Pipeline status response: {response}')
  return {
    'response': response,
    'done':     response.get('done', False),
    'error':    response.get('error', False),
  }

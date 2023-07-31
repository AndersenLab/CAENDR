import requests

from caendr.services.logger import logger

from .cloudrun     import get_job_execution_status
from .lifesciences import get_pipeline_status

from caendr.models.datastore  import PipelineOperation
from caendr.models.error      import APINotFoundError
from caendr.services.email    import send_email

from caendr.services.cloud.secret import get_secret
from caendr.utils.env import get_env_var



MODULE_SITE_HOST      = get_env_var('MODULE_SITE_HOST')
API_SITE_ACCESS_TOKEN = get_secret('CAENDR_API_SITE_ACCESS_TOKEN')
NO_REPLY_EMAIL        = get_secret('NO_REPLY_EMAIL')



def get_operation_status(operation_name):
  '''
    Request the operation status from the correct pipeline, based on the service name.
  '''

  # Get the service & operation ID from the full operation name
  try:
    service, op_id = operation_name.split('/')[-2:]
  except:
    raise ValueError(f'Invalid operation name "{operation_name}"')

  # Life Sciences Pipeline
  if service == 'operations':
    logger.warn(f"[UPDATE {op_id}] Getting GLS pipeline status...")
    return get_pipeline_status(operation_name), service, op_id

  # Cloud Run Execution
  elif service == 'executions':
    logger.warn(f"[UPDATE {op_id}] Getting Cloud Run execution status...")
    return get_job_execution_status(operation_name), service, op_id

  # If nothing matched, return an error
  raise ValueError(f'Invalid service name "{service}".')



def update_pipeline_operation_record(operation_name):
  '''
    Update the status fields of a pipeline operation record based on the current status of the pipeline itself.
  '''

  # Get the operation status, plus the parsed service & id values
  try:
    status, service, op_id = get_operation_status(operation_name)

  # Operation could not be found
  except Exception as ex:
    raise APINotFoundError(f'Operation "{operation_name}" NOT FOUND in service "{service}". Nothing to do.') from ex

  # Try getting the operation record
  # Raises NotFound error if record doesn't exist
  op = PipelineOperation.get_ds(op_id, silent=False)

  # Update and return the record object
  logger.info(f"[UPDATE {id}] Done = {status.get('done')}, Error = {status.get('error')}")
  op.set_properties(**{
    'done':  status.get('done'),
    'error': status.get('error'),
  })
  op.save()
  return op



def send_result_email(record, status):

  response = requests.get(
    f'https://{MODULE_SITE_HOST}/api/notifications/job-finish/{record.kind}/{record.id}/{status}',
    headers={
      'Content-Type':  'application/json',
      'Authorization': 'Bearer {}'.format(API_SITE_ACCESS_TOKEN),
    },
  )

  # Get the JSON body from the request
  if response.status_code != 200:
    return response
  message = response.json()

  # Send the email
  return send_email({
    "from":    f'CaeNDR <{NO_REPLY_EMAIL}>',
    "to":      record.get_user_email(),
    "subject": f'Your {record.get_report_display_name()} Report from CaeNDR.org',
    "text":    message['text'],
    "html":    message['html'],
  })

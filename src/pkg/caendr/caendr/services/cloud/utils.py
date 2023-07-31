from caendr.services.logger import logger

from .cloudrun     import get_job_execution_status
from .lifesciences import get_pipeline_status

from caendr.models.datastore  import PipelineOperation
from caendr.models.error      import APINotFoundError



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

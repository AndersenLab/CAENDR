from caendr.services.logger import logger
from caendr.utils.env       import get_env_var

from caendr.models.datastore             import Species
from caendr.models.error                 import APIBadRequestError, NotFoundError
from caendr.models.job_pipeline          import JobPipeline, get_pipeline_class
from caendr.services.nemascan_mapping    import update_nemascan_mapping_status
from caendr.services.database_operation  import update_db_op_status
from caendr.services.indel_primer        import update_indel_primer_status
from caendr.services.heritability_report import update_heritability_report_status



# Get environment variables
DB_OPERATIONS_TASK_QUEUE_NAME = get_env_var('MODULE_DB_OPERATIONS_TASK_QUEUE_NAME')
INDEL_PRIMER_TASK_QUEUE_NAME  = get_env_var('INDEL_PRIMER_TASK_QUEUE_NAME')
HERITABILITY_TASK_QUEUE_NAME  = get_env_var('HERITABILITY_TASK_QUEUE_NAME')
NEMASCAN_TASK_QUEUE_NAME      = get_env_var('NEMASCAN_TASK_QUEUE_NAME')



def get_task_handler(queue_name, *args, **kwargs):
  '''
    Args:
      - queue_name: The queue to run the job in.
      - kwargs: The job payload.
  '''
  try:
    cls = get_pipeline_class(queue = queue_name)

  except ValueError:
    raise APIBadRequestError(f'Invalid task route {queue_name}')

  try:
    return cls.lookup(kwargs['id'])

  except NotFoundError as ex:
    if ex.kind == Species.kind:
      raise APIBadRequestError(f'{ cls.get_kind() } task has invalid species value') from ex
    else:
      raise APIBadRequestError(f'Could not find { cls.get_kind() } object wih this ID') from ex



def update_status_safe(queue_name, op_id, call_id='', status=None, **kwargs):
  '''
    Safely update the TaskStatus of the given Entity.
    Logs & ignores errors.
  '''

  # Mapping of queues to status update functions
  MAPPING = {
    DB_OPERATIONS_TASK_QUEUE_NAME: update_db_op_status,
    INDEL_PRIMER_TASK_QUEUE_NAME:  update_indel_primer_status,
    HERITABILITY_TASK_QUEUE_NAME:  update_heritability_report_status,
    NEMASCAN_TASK_QUEUE_NAME:      update_nemascan_mapping_status,
  }

  # Try running the appropriate update function, forwarding any extra keywords
  try:
    # _update_status(queue_name, op_id, status=status, **kwargs)
    return MAPPING[queue_name](op_id, status=status, **kwargs)

  # If update failed, log the exception and ignore
  except Exception as ex:
    msg = f'Failed to update status to { status }: { ex }'
    if call_id:
      logger.error(f'[{ call_id }] { msg }')
    else:
      logger.error(msg)

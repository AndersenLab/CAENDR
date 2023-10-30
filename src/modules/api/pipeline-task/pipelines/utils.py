import json
from typing import Tuple, Optional

from caendr.services.logger import logger

from caendr.models.datastore    import Species
from caendr.models.error        import APIBadRequestError, APINotFoundError, NotFoundError
from caendr.models.job_pipeline import JobPipeline, get_pipeline_class, pipeline_subclasses
from caendr.models.status       import JobStatus
from caendr.models.run          import GCPCloudRunRunner



def load_json_from_request(request):
  '''
    Loads the request data as JSON.
    Raises a 400 error if the body is not valid JSON.
  '''
  try:
    return json.loads(request.data)
  except Exception as ex:
    raise APIBadRequestError('Failed to parse request body as valid JSON') from ex



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
      raise APINotFoundError(f'Could not find { cls.get_kind() } object wih this ID') from ex



def get_runner_from_operation_name(operation_name: str) -> Tuple[GCPCloudRunRunner, Optional[str]]:
  '''
    Convert an operation name into a Runner subclass of the appropriate type,
    along with the corresponding execution name (if available).

    TODO: This implicitly relies on no kind being a prefix of any other kind.
          This lets us make no assumptions about the presence of dashes in the kind and data ID,
          since a dash is used for two purposes:
            - To separate the kind from the data ID
            - To replace underscores in both the kind and the data ID
          We have that situation currently, but will this always hold? Is there a safer way to rename these?

          Alternatively - even if there is a namespace collision, we can just check the status for all matching jobs.
          Running the status check again on a job that's already complete shouldn't interfere with it,
          and running the status check multiple times on a still running job will be fine(?)
          We'd have to explicitly handle the multiple value case, and only return 200 OK when all are complete.
  '''

  # Try parsing from operation name for each subclass, skipping if name is invalid for that subclass
  results = []
  for cls in pipeline_subclasses:
    try:
      results.append( cls._Runner_Class.from_operation_name(cls.get_kind(), operation_name) )
    except:
      pass

  # If none of the subclasses accepted the operation name, it is invalid
  if len(results) == 0:
    raise APIBadRequestError(f'Operation "{operation_name}" NOT FOUND -- nothing to do')

  # If more than one subclass accepted, there was a name collision(!)
  elif len(results) > 1:
    raise APIBadRequestError(f'Operation "{operation_name}" matched multiple jobs')

  # Try getting an execution ID from the operation name, defaulting to None
  try:
    exec_id = results[0].get_execution_id_from_operation_name( operation_name )
  except ValueError:
    exec_id = None

  # Return the one matching subclass object, and the execution ID
  return results[0], exec_id



def update_status_safe(job: JobPipeline, status: JobStatus, call_id: str):
  '''
    Safely update the JobStatus of the given job's report.
    Logs & ignores errors.
  '''

  # Log the operation
  logger.debug(f'[{ call_id }] Updating status to "{ status }"...')

  # Try setting the status property of the report
  try:
    job.report['status'] = status
    job.report.save()

  # If update failed, log the exception and ignore
  except Exception as ex:
    logger.error(f'[{ call_id }] Failed to update status to { status }: { ex }')

from googleapiclient import discovery
from googleapiclient.errors import HttpError
from oauth2client.client import GoogleCredentials

from caendr.services.logger import logger

from caendr.utils.env import get_env_var



# Load environment variables
GOOGLE_CLOUD_PROJECT_NUMBER = get_env_var('GOOGLE_CLOUD_PROJECT_NUMBER')
GOOGLE_CLOUD_PROJECT_ID     = get_env_var('GOOGLE_CLOUD_PROJECT_ID')
GOOGLE_CLOUD_REGION         = get_env_var('GOOGLE_CLOUD_REGION')
GOOGLE_CLOUD_ZONE           = get_env_var('GOOGLE_CLOUD_ZONE')
SERVICE_ACCOUNT_NAME        = get_env_var('MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME')


# Create the CloudRun service using the v2 API
SERVICE = discovery.build('run', 'v2', credentials=GoogleCredentials.get_application_default())

parent_id = f"projects/{GOOGLE_CLOUD_PROJECT_NUMBER}/locations/{GOOGLE_CLOUD_REGION}"
sa_email  = f"{SERVICE_ACCOUNT_NAME}@{GOOGLE_CLOUD_PROJECT_ID}.iam.gserviceaccount.com"



def create_job(name, task_count, timeout, max_retries, container, update_if_exists=True):
  '''
    Create a CloudRun job.
    For more details, see https://googleapis.github.io/google-api-python-client/docs/dyn/run_v2.projects.locations.jobs.html#create

    Args:
      - name (str): The ID of the job in CloudRun
      - task_count (int): The number of separate tasks to run in a single job execution
      - timeout (str): The amount of time to allocate for running the job
      - max_retries (int): The total number of times to try running the job, if one or more executions fail
      - container: An object that configures the container to be run.
      - update_if_exists: If True, if a job with this name already exists, update its fields and run a new execution. If False, raises an error if the job already exists.

    Returns:
      A response object.
  '''
  body = {
    'launchStage':        'BETA',  # Required for jobs longer than 1hr
    'template': {
      'taskCount':        task_count,
      'template': {
        'maxRetries':     max_retries,
        'timeout':        timeout,
        'containers':     [ container ],
        'serviceAccount': sa_email,
      },
    }
  }

  # If desired, create/update the job
  if update_if_exists:
    try:
      return SERVICE.projects().locations().jobs().patch( name=f'{parent_id}/jobs/{name}', allowMissing=True, body=body).execute()

    # If the request returns a 404, ignore it and fall-through -- i.e. try creating the job directly
    # The `allowMissing` param above should handle this, but in my experience it doesn't
    except HttpError as ex:
      if ex.status_code == 404:
        logger.warn(f'Ignoring error patching job: {ex}')
      else:
        raise

  # Otherwise, try creating the job, and propagate the error if it already exists
  return SERVICE.projects().locations().jobs().create( parent=parent_id, jobId=name, body=body ).execute()


def run_job(name):
  '''
    Run a CloudRun job.

    Args:
      - name (str): The ID of the job in CloudRun

    Returns:
      A request object that can be executed using .execute()
  '''
  return SERVICE.projects().locations().jobs().run( name=f'{parent_id}/jobs/{name}' ).execute()


def get_job_execution_status(name):
  '''
    Retrieve the status of a job execution.

    Returns:
      A dict object with the following fields:
        - response: The response object from GCP
        - done (bool): Whether the job has finished running.
        - error (str | None): The error message if an error occurred, or None if no error.
  '''
  response = SERVICE.projects().locations().jobs().executions().get( name=name ).execute()

  done  = False
  error = None

  # TODO: Make sure this is adequate
  for condition in response['conditions']:
    if condition['type'] == 'Completed' and condition['state'] == 'CONDITION_SUCCEEDED':
      done = True
    if condition['state'] == 'CONDITION_FAILED':
      error = condition['message']

  return {'done': done, 'error': error, 'response': response}

# Built-in libraries
from abc import ABC, abstractmethod

# Logging
from caendr.services.logger import logger

# CaeNDR package
from caendr.models.datastore  import User, Container, DataJobEntity
from caendr.models.error      import (
  NotFoundError,
  CachedDataError,
  DuplicateDataError,
  DataFormatError,
  UnschedulableJobTypeError,
  JobAlreadyScheduledError
)
from caendr.models.run        import Runner
from caendr.models.status     import JobStatus
from caendr.models.task       import Task
from caendr.utils.env         import get_env_var



# Project Environment Variables
GOOGLE_CLOUD_PROJECT_NUMBER = get_env_var('GOOGLE_CLOUD_PROJECT_NUMBER')
GOOGLE_CLOUD_PROJECT_ID     = get_env_var('GOOGLE_CLOUD_PROJECT_ID')
GOOGLE_CLOUD_REGION         = get_env_var('GOOGLE_CLOUD_REGION')
GOOGLE_CLOUD_ZONE           = get_env_var('GOOGLE_CLOUD_ZONE')

# Module Environment Variables
SERVICE_ACCOUNT_NAME        = get_env_var('MODULE_API_PIPELINE_TASK_SERVICE_ACCOUNT_NAME')
PUB_SUB_TOPIC_NAME          = get_env_var('MODULE_API_PIPELINE_TASK_PUB_SUB_TOPIC_NAME')
WORK_BUCKET_NAME            = get_env_var("MODULE_API_PIPELINE_TASK_WORK_BUCKET_NAME")
DATA_BUCKET_NAME            = get_env_var("MODULE_API_PIPELINE_TASK_DATA_BUCKET_NAME")

# Service Account & Pub/Sub Info
sa_email = f"{SERVICE_ACCOUNT_NAME}@{GOOGLE_CLOUD_PROJECT_ID}.iam.gserviceaccount.com"
pub_sub_topic = f'projects/{GOOGLE_CLOUD_PROJECT_ID}/topics/{PUB_SUB_TOPIC_NAME}'
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]



class JobPipeline(ABC):
  '''
    Template class for pipeline jobs.

    Serves as a manager for the following classes:
      - Report: Controls storage for a job (metadata + input/output data)
      - Task:   Controls scheduling of a job (submission to queue)
      - Runner: Controls running of a job
  '''

  # Custom class that defines storage
  # Must define the following methods:
  #   - check_cached_submission
  #   - set_container
  #   - set_user
  #   - save
  # Must provide [] access to fields
  # Must contain fields:
  #   - status
  # Must contain prop:
  #   - data_hash
  _Report_Class = None

  # Defines submission of a job from the site to the appropriate queue
  # If left undefined, scheduling of this job type is considered impossible
  # Must define a method "submit"
  _Task_Class   = None

  # Defines running a job container in the cloud service provider
  _Runner_Class = None

  # Associated data classes
  _Container_Class = Container
  _User_Class      = User

  _Container_Name = None


  #
  # Initialization
  #

  def __init__(self, job_id=None, report: DataJobEntity = None):
    '''
      JobPipeline objects should NOT be directly instantiated. Instead, new objects should be created using one of the following class methods:
        - create: Create a new Job, storing it in the cloud
        - lookup: Retrieve an existing Job from the cloud
    '''

    # Check that exactly one of the two optional arguments is defined, using XOR
    if not ((job_id is None) ^ (report is None)):
      raise ValueError('Exactly one of "job_id" and "report" should be provided.')

    # Job ID is defined -- instantiate the report using the Report class
    if report is None:
      report = self.create_report(job_id)
      if not report._exists:
        raise NotFoundError(self._Report_Class, {'id': job_id})

    # Confirm the report kind and JobPipeline kind match
    if report.kind != self.kind:
      raise ValueError(f'Report with incorrect kind "{report.kind}" provided to JobPipeline class "{self.kind}".')

    # Save the report to this object
    self._report = report

    # Create a managed Runner object
    # TODO: Better management of Runner object
    self._runner = self.create_runner(report=report)


  @classmethod
  def lookup(cls, job_id):
    '''
      Lookup an existing job by ID.

      Arguments:
        job_id: The unique ID of the job.

      Returns:
        A newly-created JobPipeline representing the given job.

      Raises:
        ValueError: No job with this ID could be found.
    '''
    return cls(job_id=job_id)


  @classmethod
  def create(cls, user, data, container_version=None, no_cache=False, valid_file_extensions=None):
    '''
      Create a job with the given data for the given user.
      Checks for cached submissions and cached results as defined in _Report_Class.

      Arguments:
        user: The user submitting the job.
        data: The user's input data. Will be run through subclass .parse() and used to populate the report.
        container_version:
          The version of the tool container to use. If None is provided, uses the most recent version.
          Defaults to None.
        no_cache (bool): Whether to skip checking cache (True) or not. Defaults to False.

      Returns:
        A newly-created JobPipeline representing this job.

      Raises:
        DuplicateDataError:
          If this user has already submitted this data. Contains existing Entity as first argument.
        CachedDataError:
          If another user has already submitted this job. Contains new Entity representing this user's
          submission, linked to the cached results.
    '''

    # Log the start of the creation process
    logger.debug(f'Creating new {cls._Report_Class.__name__} job for user "{user.name}".')

    # Load container version info
    container = Container.get(cls._Container_Name, version = container_version)
    logger.debug(f"Creating {cls._Report_Class.__name__} with Container {container.uri()}")
    if container_version is not None:
      logger.warn(f'Container version {container_version} was specified manually - this may not be the most recent version.')

    # Parse the input data
    parsed_data = cls.parse(data, valid_file_extensions=valid_file_extensions)

    # Check if user has already submitted this job, and "return" it in a duplicate data error if so
    if parsed_data.get('hash') and not no_cache:
      cached_report = cls.check_cached_submission(parsed_data['hash'], user.name, container, status=JobStatus.NOT_ERR)
      if cached_report:
        raise DuplicateDataError(cls.lookup(cached_report.id))

    # Create a new report to represent this job, and set data fields based on the parsed input
    report = cls.create_report(**parsed_data['props'])

    # Set the data hash for the new report based on the parsed input, if applicable
    if parsed_data.get('hash'):
      report.data_hash = parsed_data['hash']

    # Set the new report's container & user
    report.set_container(container)
    report.set_user(user)

    # Initialize the report status
    report['status'] = JobStatus.CREATED

    # Upload the new report to the cloud storage provider
    report.save()

    # Wrap the new report in a new JobPipeline object, upload the input data file(s) to data store, and return the new job
    job = cls(report=report)
    job.upload(parsed_data.get('files', []))
    return job



  #
  # Creating managed classes
  #

  @classmethod
  def create_report(cls, *args, **kwargs) -> DataJobEntity:
    return cls._Report_Class(*args, **kwargs)

  @classmethod
  def create_task(cls, *args, **kwargs) -> Task:
    return cls._Task_Class(*args, **kwargs)
  
  @classmethod
  def create_runner(cls, *args, **kwargs) -> Runner:
    return cls._Runner_Class(*args, **kwargs)



  #
  # Basic Properties
  # Mostly convenience functions for lookups, which prevent setting values
  #

  @property
  def report(self) -> DataJobEntity:
    return self._report

  @property
  def kind(self):
    '''
      Get the unique kind specified by the associated Report class.
    '''
    return self._Report_Class.kind

  @classmethod
  def get_kind(cls):
    '''
      Class-level method for getting kind.
    '''
    return cls._Report_Class.kind

  @property
  def queue(self):
    '''
      Get the queue name specified by the associated Task class.
    '''
    return self._Task_Class.queue

  @classmethod
  def get_queue(cls):
    '''
      Class-level method for getting queue name.
    '''
    return cls._Task_Class.queue



  #
  # Image & Container Properties
  # Lookup / construct information about the container image & container used to run this job
  #

  @property
  def image_uri(self) -> str:
    '''
      The URI for this job's container image. Used to look up & create the container.
    '''
    return self.report.get_container().uri()
  
  @property
  def image_version(self) -> str:
    '''
      The version of this job's container image.
    '''
    return self.report.container_version



  #
  # Parsing
  # Convert user input into a report
  #

  @classmethod
  @abstractmethod
  def parse(cls, data: dict, valid_file_extensions = None) -> dict:
    '''
      Parse user input into properties to be stored in the report object (in the cloud).
      If any validation is required, it should be performed here.

      By default, uses the data dictionary as the set of props with no modification.

      Args:
        - data (dict): The input data.

      Returns:
        A dictionary with the following fields:
          - props (dict): A dict of fields to save to the Report object.
          - hash (str):   A unique hash for this input data. Optional.
          - files (list): A list of files to upload to cloud storage. These will be handled by the `upload` method. Optional.

      Raises:
        - PreflightCheckError: One or more required files were not found in cloud storage.
        - DataFormatError:     Validation of the input failed.
    '''
    return { 'props': data }



  #
  # Caching
  #

  @classmethod
  def check_cached_submission(cls, *args, **kwargs):
    '''
      Check whether this user has submitted this job before.
    '''
    # Forward cache check to Report class
    return cls._Report_Class.check_cached_submission(*args, **kwargs)



  #
  # File Storage
  # Uploading & downloading files to/from the cloud storage provider
  #

  @abstractmethod
  def upload(self, data_files: list):
    '''
      Upload the data for this job to the cloud.

      Args:
        - data_files (list): A list of files to upload to cloud storage. May be empty.
    '''
    pass



  #
  # Scheduling
  #

  @property
  def is_schedulable(self) -> bool:
    '''
      Whether jobs of this type can be scheduled.
      Checks whether this subclass defines a Task class.
    '''
    return self._Task_Class is not None


  def schedule(self, no_cache=False, force=False) -> JobStatus:
    '''
      Submit a job to the appropriate queue, using the assigned Task class.

      Returns:
        The new JobStatus of this job, with one of the following values:
          - SUBMITTED: The task was successfully submitted to the appropriate queue
          - ERROR: There was a problem submitting the task to the appropriate queue

      Raises:
        - UnschedulableJobTypeError:
            This job's subclass does not assign a Task class, i.e. scheduling is impossible.
        - JobAlreadyScheduledError:
            This specific job has already been scheduled. Will not re-schedule the job.
            This behavior can be disabled by setting `force` to True. Note that this may re-schedule an existing job.
        - CachedDataError:
            Results have already been computed for this job's input data. Will not re-schedule the job.
            This behavior can be disabled by setting `no_cache` to True. Note that this may re-schedule a job.
    '''

    # If Task class is not defined, scheduling is not supported for this job type
    if not self.is_schedulable:
      raise UnschedulableJobTypeError()

    # Check whether this specific job has already been scheduled
    # If force is True, this check will not be run
    if not force and self.report['status'] != JobStatus.CREATED:
      raise JobAlreadyScheduledError()
    
    # If using cache, check whether this job already has results and short-circuit the computation if so
    # If no_cache is True, this check will not be run
    if not no_cache and self._check_cached_result():
      raise CachedDataError()

    # Schedule job in task queue
    task   = self.create_task(self.report)
    result = task.submit()

    # Update entity status to reflect whether task was submitted successfully
    self.report['status'] = JobStatus.SUBMITTED if result else JobStatus.ERROR
    self.report.save()

    # Return the status
    # TODO: Raise an error if submission fails?
    return self.report['status']



  #
  # Running
  #

  def run(self, *args, **kwargs):
    '''
      Run this job using the specified Runner class.
    '''

    # Check if this report is already associated with an operation
    if self.report['operation_name'] is not None:
      logger.warn(f'Report {self.report.id} (data hash {self.report.data_hash}) is already associated with operation {self.report["operation_name"]}. Running again...')

    # Forward run call to Runner object
    exec_id = self._runner.run(self.report, *args, **kwargs)

    # Save the full execution name to the report object, so it can be looked up later
    self.report['operation_name'] = self._runner.get_full_execution_name(exec_id)
    self.report.save()

    # Return the execution ID
    return exec_id


  #
  # Status
  #

  def _check_cached_result(self):
    cached_result = self.report.check_cached_result()

    # If cache check returned a status, use it; otherwise, default to "COMPLETE"
    if cached_result:
      self.report['status'] = cached_result if isinstance(cached_result, str) else JobStatus.COMPLETE
      self.report.save()

    return cached_result


# def has_results
  def is_finished(self) -> bool:
    '''
      Check for results.

      Returns:
        status (JobStatus): The current status of the job
        result: The results if the job is complete, or None if no result exists.
    '''

    cached_result = self.check_cached_result()
    if cached_result:

      # If cache check returned a status, use it; otherwise, default to "COMPLETE"
      self.report['status'] = cached_result if isinstance(cached_result, str) else JobStatus.COMPLETE
      self.report.save()

    return self.report['status'] in JobStatus.FINISHED

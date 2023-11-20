class JobStatus:
  '''
    The set of possible values for the status of a job.

    The normal life cycle of a job will put it through the following chain:
      CREATED -> SUBMITTED -> RUNNING -> (COMPLETE or ERROR)

    The status values have the following meanings:
      - CREATED:   The job has been parsed, a record object has been created storing its metadata, and any relevant input files have been uploaded to the cloud
      - SUBMITTED: The job has been scheduled in the appropriate queue
      - RUNNING:   An execution has been created for the job and is running in the cloud
      - COMPLETE:  The job execution finished successfully, and output any relevant files in the cloud
      - ERROR:     The job execution failed, and may have output any relevant files / logs in the cloud
  '''

  # Basic JobStatus values
  CREATED   = "CREATED"
  ERROR     = "ERROR"
  RUNNING   = "RUNNING"
  COMPLETE  = "COMPLETE"
  SUBMITTED = "SUBMITTED"

  # Meaningful sets of JobStatus values
  FINISHED  = { COMPLETE, ERROR }
  NOT_ERR   = { SUBMITTED, RUNNING, COMPLETE }

  # Check whether a variable is a valid JobStatus
  @staticmethod
  def is_valid(value):
    return value in {
      JobStatus.CREATED,
      JobStatus.ERROR,
      JobStatus.RUNNING,
      JobStatus.COMPLETE,
      JobStatus.SUBMITTED,
    }

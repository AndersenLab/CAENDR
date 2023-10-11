# Parent Class & Models
from .job_pipeline           import JobPipeline
from caendr.models.datastore import DatabaseOperation
from caendr.models.run       import DatabaseOperationRunner
from caendr.models.task      import DatabaseOperationTask

# Services
from caendr.utils.env        import get_env_var


DB_OPERATIONS_CONTAINER_NAME = get_env_var('MODULE_DB_OPERATIONS_CONTAINER_NAME')



class DatabaseOperationPipeline(JobPipeline):

  _Report_Class = DatabaseOperation
  _Task_Class   = DatabaseOperationTask
  _Runner_Class = DatabaseOperationRunner

  _Container_Name = DB_OPERATIONS_CONTAINER_NAME



  # TODO: The following methods are required by the Abstract parent

  @classmethod
  def parse(cls, data, delimiter='\t'):
    return super()

  def upload(self, data_files):
    return
